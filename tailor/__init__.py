#!/usr/bin/env python

from os import walk, path, remove
from paramiko import SSHClient
from logging import getLogger, WARNING
from stat import S_ISDIR, S_ISREG, S_ISLNK

class TailorException(Exception):
    pass

class UnknownOSException(TailorException):
    def __init__(self, os):
        self.os = os
    def __str__(self):
        return "Unknown operating systgem {os}".format(os=self.os)

class TooManyHostsException(TailorException):
    def __str__(self):
        return "tinc-tailor can only handle 256 hosts"

class CommandFailedException(TailorException):
    def __init__(self, return_code):
        self.return_code = return_code
    def __str__(self):
        return "Command returned {return_code}".format(return_code=self.return_code)

#
# Classes for managing individual hosts
#

class Host(object):
    def __init__(self, hostname, properties={}):
        self.logger = getLogger('tailor.host.' + hostname)
        self.logger.info("Adding host '%s'", hostname)
        self.hostname = hostname.replace('-','_')
        self.client = SSHClient()
        self.client.load_system_host_keys()
        self.client.connect(hostname, username='root',key_filename=['/home/david/.ssh/id_rsa','/home/david/.ssh/id_rsa_ec2east','/home/david/.ssh/id_rsa_ec2west'])
        self.sftp = self.client.open_sftp()
        self.properties = self.get_properties()
        self.properties.update(properties)
        
    def async_command(self, command):
        chan = self.client.get_transport().open_session()
        chan.setblocking(True)
        chan.set_combine_stderr(True)
        chan.exec_command(command)
        return chan
    
    def sync_command(self, command):
        chan = self.async_command(command)
        for line in chan.makefile():
            self.logger.debug(line.strip())
        chan.recv_exit_status()
        if chan.exit_status is not 0:
            raise CommandFailedException(chan.exit_status)
        return chan.exit_status
    
    def interpolate(self, string):
        return string.format(**self.properties)
    
    def get_properties(self):
        debian_properties = {
           'addrepo_command': '',
           'update_command': 'apt-get -y --force-yes update',
           'install_command': 'apt-get -y --force-yes install',
           'remove_command': 'apt-get -y --force-yes remove'
        }
        redhat_properties = {
           'addrepo_command': 'yum -y install',
           'update_command': 'yum clean expire-cache',
           'install_command': 'yum -y install',
           'remove_command': 'yum -y remove'
        }
        stdout = self.async_command('cat /etc/issue').makefile('r')
        first = stdout.readline()
        stdout.close()
        if first.find("Debian") is not -1:
            properties = debian_properties
            properties['distribution'] = 'debian'
        elif first.find("Redhat") is not -1 or first.find("Red Hat") is not -1:
            properties = redhat_properties
            properties['distribution'] = 'redhat'
        elif first.find("CentOS") is not -1:
            properties = redhat_properties
            properties['distribution'] = 'centos'
        else:
            raise UnknownOSException(first)
        properties['hostname'] = self.hostname

        return properties

class Hostlist(object):
    def __init__(self,hosts=[], properties={}):
        self.properties = properties
        self.hosts=[]
        self.logger = getLogger('tailor.hostlist')
        self.net = 33
        self.hostnum = 1
        for host in hosts:
            self.add_host(host)
    
    def add_host(self, hostname):
        if self.hostnum >= 255:
            raise TooManyHostsException()
        host = Host(hostname, self.properties)
        host.properties['number'] = str(self.hostnum)
        host.properties['private_ipv4_subnet'] = '192.168.'+str(self.net)+'.'+ str(self.hostnum)+'/32'
        host.properties['private_ipv4_address'] = '192.168.'+str(self.net)+'.'+ str(self.hostnum)
        host.properties['private_ipv4_cidr'] = '192.168.'+str(self.net)+'.'+ str(self.hostnum)+'/24'
        host.properties['private_ipv4_netmask'] = '255.255.255.0'
        self.hosts.append(host)
        self.hostnum += 1
        
        for host in self.hosts:
            host.properties['connect_to_list'] = "\n".join('ConnectTo = ' + other_host.hostname for other_host in self.hosts if other_host.hostname is not host.hostname)
    
    def run_action(self, action):
        return [action.run(host) for host in self.hosts]
    
    def subset(self, filter_hosts):
        newlist = Hostlist(None)
        newlist.hosts = [host for host in self.hosts if host.hostname in filter_hosts]
        if len(newlist) is not len(filter_hosts):
            raise TailorException()
        return newlist
    
    def filter(self, filter_hosts):
        self.hosts = [host for host in self.hosts if host.hostname not in filter_hosts]
    
    def __len__(self):
        return len(self.hosts)
    
    def __iter__(self):
        return iter(self.hosts)

#
# Classes for doing things to hosts
#

class Action(object):
    def __init__(self):
        self.logger = getLogger('tailor.action.' + self.__class__.__name__)
        
    def run(self, host):
        pass
 
class Try(Action):
    def __init__(self, action, log_level=WARNING):
        super(Try, self).__init__()
        self.action = action
        self.log_level = log_level
    
    def run(self, host):
        try:
            self.action.run(host)
        except:
            self.action.logger.log(self.log_level,'Try Action failed', exc_info=True)
    
class Command(Action):
    def __init__(self, command):
        super(Command, self).__init__()
        self.command = command
        
    def run(self, host):
        command = host.interpolate(self.command)
        self.logger.info("Running command '%s' on host '%s'", command, host.hostname)
        host.sync_command(command)
    
class AddRepos(Action):
    def __init__(self, repos):
        self.repos = repos
        super(Addrepo, self).__init__()

    def debianrepo(self, host, repo):
        repo = host.interpolate(repo) 
        self.logger.info("Setting up repository '%s' on host '%s'", repo, host.hostname)
        host.sync_command('echo "' + repo + '" >> /etc/apt/sources.list')

    def redhatrepo(self, host, repo):
        repo = host.interpolate(repos) 
        self.logger.info("Setting up repository '%s' on host '%s'", repo, host.hostname)
        host.sync_command('{addrepo_command} ' + repo)
        
    def run(self, host):
        try:
            if host.properties['distribution'] == 'debian':
                repofn = self.debianrepo
            if host.properties['distribution'] == 'centos' or host.properties['distribution'] == 'redhat':
                repofn = self.redhatrepo   
            if isinstance(self.repos[host.properties['distribution']], str):
                self.repofn(host, self.repos[host.properties['distribution']])
            else:
                for repo in self.repos[host.properties['distribution']]:
                    self.repofn(host, repo)
        except KeyError:
            pass

class UpdateRepos(Command):
    def __init__(self):
        super(Install, self).__init__('{update_command}')

class Install(Command):
    def __init__(self, package):
        super(Install, self).__init__('{install_command} '+package)
    
class Ping(Command):
    def __init__(self, host):
        super(Ping, self).__init__('ping -c 1 -q '+host.properties['private_ipv4_address'])
    
class Uninstall(Command):
    def __init__(self, package):
        super(Uninstall, self).__init__('{remove_command} '+package)
        
class GetFile(Action):
    def __init__(self, remotename, localname):
        super(GetFile, self).__init__()
        self.remotename = remotename
        self.localname = localname
        
    def run(self, host):
        remotename = host.interpolate(self.remotename)
        self.logger.info("Fetching file '%s' from host '%s'", remotename, host.hostname)
        host.sftp.get(remotename, host.interpolate(self.localname))

class Mkdir(Action):
    def __init__(self, remotedir):
        super(Mkdir, self).__init__()
        self.dir = remotedir
        
    def run(self, host):
        remotedir = host.interpolate(self.dir)
        self.logger.info("Making directory '%s' on host '%s'", remotedir, host.hostname)
        host.sftp.mkdir(remotedir)

class Rmdir(Action):
    def __init__(self, remotedir):
        super(Rmdir, self).__init__()
        self.dir = remotedir
    
    def recursive_remove(self,host, remotedir):
        for attr in host.sftp.listdir_attr(remotedir):
            if S_ISDIR(attr.st_mode):
                self.recursive_remove(host, path.join(dir,attr.filename))
            elif S_ISREG(attr.st_mode) or S_ISLNK(attr.st_mode):
                host.sftp.remove(path.join(dir,attr.filename))
            else:
                raise IOError("Cannot remove remote file:" + str(attr))
        host.sftp.rmdir(remotedir)
    
    def run(self, host):
        remotedir = host.interpolate(self.dir)
        self.logger.info("Removing directory '%s' on host '%s'", remotedir, host.hostname)
        self.recursive_remove(host, remotedir)

class Rm(Action):
    def __init__(self, filename):
        super(Rm, self).__init__()
        self.file = filename
        
    def run(self, host):
        filename = host.interpolate(self.file)
        self.logger.info("Removing file '%s' on host '%s'", filename, host.hostname)
        host.sftp.remove(filename)

class PutFile(Action):
    def __init__(self,localname, remotename, interpolate = False):
        super(PutFile, self).__init__()
        self.remotename = remotename
        self.localname = localname
        self.interpolate = interpolate
        
    def run(self, host):
        remotename = host.interpolate(self.remotename)
        localname = host.interpolate(self.localname)
        self.logger.info("Sending file '%s' to '%s' on host '%s'", localname, remotename , host.hostname)
        if self.interpolate:
            remote = host.sftp.open(remotename, mode='w')
            with open(localname, 'r') as local:
                for line in local:
                    remote.write(host.interpolate(line))
        else:
            host.sftp.put(localname, remotename)

            
class ActionList(Action):
    def __init__(self):
        super(ActionList, self).__init__()
        self.actions = []
        
    def run(self, host):
        self.logger.debug("running %d actions", len(self.actions))
        [action.run(host) for action in self.actions]

class PutDir(ActionList):
    def __init__(self,localname, remotename):
        self.localname = localname
        self.remotename = remotename
        self.walked = False
    
    def run(self, host):
        if not self.walked:
            self.walk()
            self.walked = True
        super(PutDir,self).run(host)
    
    def walk(self):
        super(PutDir, self).__init__()
        self.logger.debug("listing %s", self.localname)
        for (dirpath, _, filenames) in walk(self.localname):
            remotedir = path.join(self.remotename, path.relpath(dirpath, self.localname))
            self.actions.append(Try(Mkdir(remotedir)))
            self.logger.debug("Mkdir %s", remotedir)
            for filename in filenames:
                fromfile = path.join(dirpath, filename)
                tofile = path.join(remotedir, filename)
                self.actions.append(PutFile(fromfile, tofile))
                self.logger.debug("Putfile %s %s", fromfile, tofile)

class Tailor(object):
    def __init__(self, params=None, properties={}):
        self.properties = properties
        if params is not None:
            self.argparse(params)
        self.hosts = Hostlist(hosts=params.hosts, properties=self.properties)
    
    @staticmethod
    def setup_argparse(parser):
        pass
    
    def argparse(self, params):
        pass
    
    def run(self):
        pass