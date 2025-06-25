# vmware-deployment-tool


----------------------------------------------------------------------------------------------------------------

- deployment.py runs the Deployment website:
    ./deployment.py
    CTRL + right click "http://10.86.36.250:8080"
    
- redLaunch.py must be running in a terminal to work in the browser, please rerun the program in case of any restarts
    https://deployment.company.local/

- Database Structure

    deploymentdb
    |
    | -> user
    | -> deployed_vm

  Users are given permission to which of the 4 functionalities they can use. Can be changed manually from the database

- Libraries used
    -flask -> Python library to work with web
    -flask_mysqldb -> To connect mysql database to website
    -ldap -> For ldap configuration
    -re
    -requests
    -json
    -time

- Functionalities
    - Virtual Machine Deployment
    - OpenShift Deployment
    - Bare Metal Deployment
    - POC Deployment

- Website structure

    redLaunch
    |
    | -> loginpage.html
         | -> it-io-deployment.html
              | -> vm_installation_1.html
              | -> vm_installation_2.html
              | -> vm_installation_3.html
              | -> vm_installation_4.html
              | -> vm_installation_5.html
              |
              | -> vmloading.html
              |
              | -> vmcreated.html
                 / vmfailed.html

-  Helper Functions

    - ldap_authentication(username, password):
       "@company.local" is added at the end of the username to be able to check ldap authentication
       
       ldap host:  ldaps://ldaps.company.local:port

       Possible errors (exceptions):
        - Invalid credentials
        - Ldap server is down

    - atoi(string):
        A regular atoi function for input_to_yml()'s use
        Converts string into integer

    - input_to_yml():
        Memory is converted to MB from GB
        Vlan name is written as the vlanID using the vlan table in database
        Variables are written into a dictionary
        VM deployment is triggered by sending an HTTP request to the ansible playbook REST API
            https://172.31.60.229/api/v2/job_templates/23/launch/
        All VM's are deployed using the "redlaunch" user
        VM deployment process is checked every 5 seconds to see if concluded using the REST API
            https://172.31.60.229/api/v2/jobs/

            Example output of a successful job:

            PLAY [Get disk size from VM template and create VM] ****************************
            TASK [create VM] ***************************************************************
            changed: [localhost]
            PLAY RECAP *********************************************************************
            localhost                  : ok=1    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0 


            Example output of a failed job:

            PLAY [Get disk size from VM template and create VM] ****************************
            TASK [create VM] ***************************************************************
            fatal: [localhost]: FAILED! => {"changed": false, "msg": "Could not find a template named sometemplate"}
            PLAY RECAP *********************************************************************
            localhost                  : ok=0    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0 
        VM properties are inserted into the deployed_vmtable in the database
            - username
            - vcenter
            - template
            - vm name
            - ip address
            - cpu number
            - memory

    - datacenterbyvcenter(vcenter_name):
        Gets datacenters filtered by vcenter
    
    - templatebyvcenter(vcenter_name):
        Gets templates filtered by vcenter

    - folderbydatacenter(datacenter_name, vcenter_name):
        Gets folders filtered by datacenter

    - clusterbydatacenter(datacenter_name, vcenter_name):
        Gets clusters filtered by datacenter

    - datastoreclusterbycluster(cluster_name, vcenter_name):
        Gets datastoreclusters filtered by cluster

    - vlanbycluster(cluster_name, vcenter_name):
        Gets vlans filtered by vcenter
        
- Individual Pages

    - loginpage():
        Checks the ldap username and password's correctness

    - redLaunch():
        Checks the user's role from the "user" table in the database
        Enables/Disables the buttons that user can proceed with
    
    - vm_installation_1():
        Gets vcenters from the vcenter table
            - datacenters from the datacenter table
            - clusters from the cluster table
            - folders from the folder table
            - datastoreclusters from the datastorecluster table

    - vm_installation_2():
        Gets templates from the template table
        Gets vm name, memory and cpu from the user

    - vm_installation_3():
        Gets vlans from the vlan table
        Gets ip address, netmask and gateway from the user

    - vm_installation_4():
        Gets disk number and disk sizes from the user

    - vm_installation_5():
        Shows user the summary of the vm properties

    - vmloading():
        Shows the vmloading.html page

    - vmcreated():
        Shows the vm properties in the "successful" page

    - vmfailed():
        Shows the error message in the "failed" page
----------------------------------------------------------------------------------------------------------------
