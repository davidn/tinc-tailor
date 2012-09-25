
`tinc-tailor`
=============

`tinc-tailor` is a tool for managing a cluster of servers using
[`tinc`](http://www.tinc-vpn.org/).


`hosts.list`
------------

This is a list of hostnames, one per line, that `tinc-tailor` considers to be
in the cluster.  You should ensure the hostnames have no hyphens in them as
`tinc` does not like this. You should also ensure all the hosts and your
workstation can reach each other by these hostnames.


command reference
-----------------

*  `tinc-tailor install *host1* *host2* ...`

   This performs the initial setup of these hosts, adding them to the cluster.
   Note that they must already be added to the `hosts.list` file. 

*  `tinc-tailor remove *host1* *host2* ...`

   This removes the given hosts from the cluster, and removes tinc from them.
   The hosts should be removed from `hosts.list` after this is run.

*  `tinc-tailor test`

   This makes every host in `hosts.list` ping every other host by their private
   address
   

options
-------

`tinc-tailor` has some options to customize it's behavior:

* `--log-level (DEBUG|INFO|WARNING|ERROR|FATAL)`

* `--netname NETNAME`

examples
--------

Installing two nodes:

    $ cat > hosts.list
    node1.publicnetwork.com
    node2.publicnetwork.com
    $ ./tinc-tailor install node1.publicnetwork.com node2.publicnetwork.com

Verifying they work:

    $ ./tinc-tailor test

Adding an extra node:

    $ cat >> host.list
    ondemand.cloudprovider.com
    $ ./tinc-tailor install ondemand.cloudprovider.com

Removing the first node:

    $ cat > host.list
    node1.publicnetwork.com
    ondemand.cloudprovider.com
    $ ./tinc-tailor remove node2.publicnetwork.com