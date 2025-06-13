#!/ml/anaconda3/bin/python3

from flask import Flask, render_template, request, redirect, url_for, session, json, jsonify
from flask_mysqldb import MySQL
from pprint import pprint
import ldap
import re
import requests
import json
import time
import os
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "super secret key"
app.debug = True

app.config['MYSQL_HOST'] = 'db_host'
app.config['MYSQL_USER'] = 'db_username'
app.config['MYSQL_PASSWORD'] = 'db_password'
app.config['MYSQL_DB'] = 'db_name'

mysql = MySQL(app)

vcenter_username = "vcenter_service_user_username"
vcenter_password = "vcenter_service_user_password"

def ldap_authentication(username, password):
    user = username + "local_domain_name"

    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    conn = ldap.initialize('ldaps://ldaps.local_domain_name:port')

    conn.protocol_version = 3
    conn.set_option(ldap.OPT_REFERRALS, 0)

    try:
        conn.simple_bind_s(user, password)
    except ldap.INVALID_CREDENTIALS:
        print("Invalid credentials")
        return 'loginpage'
    except ldap.SERVER_DOWN:
        print("Ldap server down")
        return 'loginpage'
    else:
        base_dn = 'dc=domain,dc=local'
        search_filter = '(cn='+ username +')'
        attributes = ['cn', 'mail']
        
        result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter, attributes)
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE user SET email=%s WHERE userName = %s", (result[0][1]['mail'], session['username']))
        mysql.connection.commit()
        
        conn.unbind_s()
        return 'successful'

@app.route('/vm_input_to_yml', methods=['GET', 'POST'])
def vm_input_to_yml():
  
  memory = atoi(session['memory']) * 1024
  cpu = atoi(session['cpu'])
  
  cur = mysql.connection.cursor()
  cur.execute("SELECT vlanID FROM vlan WHERE vlanName = %s", [session['vlan']])
  vlanID = cur.fetchone()
 
  vlan = atoi(vlanID[0])

  disks = []

  for disk in session['disks']:
      disks.append({
          "size_gb": int(disk),
          "type": "thick",
          "datastore": session['datastore_cluster']
      })
  
  vars_dict = {
    "extra_vars": {
      'vcenter_username': vcenter_username,
      'vcenter_password': vcenter_password,
      'vcenter_hostname': session['vcenter'],
      'vcenter_datacenter': session['datacenter'],
      'vcenter_validate_certs': False,
      'vcenter_cluster': session['cluster'],
      'vm_name': session['name'],
      'vcenter_destination_folder': session['folder'],
      'vm_state': 'poweredon',
      'vm_template': session['template'],
      'memory_mb': memory,
      'num_cpus': cpu,
      'network_name': session['vlan'],
      'vlan_id': vlan,
      'ip': session['ip'],
      'netmask': session['netmask'],
      'gateway': session['gateway'],
      'vm_disks': disks
    }
  }
  
  headers = {'Content-Type': 'application/json'}
  data = json.dumps(vars_dict, indent=4)

  response = requests.post('https://172.31.60.229/api/v2/job_templates/23/launch/', headers=headers, data =data, verify=False, auth=(ansible_automation_username, ansible_automation_password))
  
  base_url = "https://172.31.60.229/api/v2/jobs/" + str(response.json().get("job")) + "/stdout/?format=txt"
  response = requests.get(base_url, verify=False, auth=(ansible_automation_username, ansible_automation_password))

  time.sleep(1)

  while "ok=0" not in response.text:
    time.sleep(5)
    response = requests.get(base_url, verify=False, auth=(ansible_automation_username,vs))

    if "failed=1" in response.text:
      match = re.search(r'"msg": "(.*)"', response.text)
      if match:
        session['log_message'] = match.group(1).strip()
        return redirect(url_for('vmfailed')) 
          
    elif "ok=1" in response.text:
      cur = mysql.connection.cursor()
      cur.execute("INSERT INTO deployed_vm (userName, vcenterName, templateName, vmName, ipAddress, cpuNumber, memory) VALUES (%s, %s, %s, %s, %s, %s, %s);", (session['username'], session['vcenter'], session['template'], session['name'], session['ip'], session['cpu'], session['memory']))
      mysql.connection.commit()
      
      return redirect(url_for('vmcreated'))

def atoi(string):
    res = 0
 
    for i in range(len(string)):
        res = res * 10 + (ord(string[i]) - ord('0'))
 
    return res

@app.route('/vm_deployment_1', methods=['GET', 'POST'])
def vm_deployment_1():
    cursor = mysql.connection.cursor()
    query = "SELECT vcentername FROM vcenter"
    cursor.execute(query)
    vcenters = cursor.fetchall()
    
    vcenterArray = []
    for row in vcenters:
        vcenterArray.append(row[0])

    vcenterArray.sort()

    vcenter = session.get('vcenter', '')
    datacenter = session.get('datacenter', '')
    cluster = session.get('cluster', '')
    folder = session.get('folder', '')
    datastoreCluster = session.get('datastore_cluster', '')

    if request.method == 'POST':
      if 'previous' in request.form:
          return redirect(url_for('it_io_deployment'))
      elif 'next' in  request.form:
          session['vcenter'] = request.form['vcenter']
          session['datacenter'] = request.form['datacenter']
          session['cluster'] = request.form['cluster']
          session['folder'] = request.form['folder']
          session['datastore_cluster'] = request.form['datastoreCluster']
          
          return redirect(url_for('vm_deployment_2'))
    return render_template(
      'vm_deployment_1.html',
      vcenters=vcenterArray,
      vcenter=vcenter,
      datacenter=datacenter,
      cluster=cluster,
      folder=folder,
      datastoreCluster=datastoreCluster
    )    
    
@app.route('/vm_deployment_2', methods=['GET', 'POST'])
def vm_deployment_2():
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT templateName FROM template WHERE vcenterName = %s", [session['vcenter']])
    templates = cur.fetchall()
    templateArray = []
    
    for row in templates:
        templateArray.append(row[0])

    templateArray.sort()

    if request.method == 'POST':
      if 'previous' in request.form:
        return redirect(url_for('vm_deployment_1'))
      elif 'next' in  request.form:
        session['template'] = request.form['template']
        session['name'] = request.form['name']
        session['memory'] = request.form['memory']
        session['cpu'] = request.form['cpu']
        
        return redirect(url_for('vm_deployment_3'))
        
    return render_template('vm_deployment_2.html', templates=templateArray) 
    
@app.route('/vm_deployment_3', methods=['GET', 'POST'])
def vm_deployment_3():
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT vlanName FROM vlan WHERE dswitchName IN (SELECT dswitchName FROM host_dswitch WHERE hostName IN (SELECT hostName FROM host_cluster WHERE vcenterName = %s AND clusterName = %s))", [session['vcenter'], session['cluster']])
    vlans = cur.fetchall()
    vlanArray = []
    for row in vlans:
        vlanArray.append(row[0])
    vlanArray.sort()
    
    if request.method == 'POST':
      if 'previous' in request.form:
        return redirect(url_for('vm_deployment_2'))
      elif 'next' in  request.form:
        session['vlan'] = request.form['vlan']
        session['ip'] = request.form['ip']
        session['netmask'] = request.form['netmask']
        session['gateway'] = request.form['gateway']
        
        return redirect(url_for('vm_deployment_4'))
        
    return render_template('vm_deployment_3.html', vlans=vlanArray) 
    
@app.route('/vm_deployment_4', methods=['GET', 'POST'])
def vm_deployment_4():
    
    if request.method == 'POST':
      if 'previous' in request.form:
        return redirect(url_for('vm_deployment_3'))
      elif 'next' in  request.form:
        session['diskCount'] = request.form['diskCount']
        
        session['disks'] = []
        
        for count in range(1, atoi(session['diskCount'])+1):
          disk = "disk" + str(count)
          session['disks'].append(request.form[disk])
        
        return redirect(url_for('vm_deployment_5'))
        
    return render_template('vm_deployment_4.html') 
    
@app.route('/vm_deployment_5', methods=['GET', 'POST'])
def vm_deployment_5():
    disks = ''

    for disk in session['disks']:
      disks = disks + str(disk) + 'GB, '

    disks = disks[:-2]

    memory = str(session['memory']) + ' GB'

    if request.method == 'POST':
      if 'previous' in request.form:
        return redirect(url_for('vm_deployment_4'))
      elif 'next' in  request.form:
        return redirect(url_for('vmloading'))
        
    return render_template('vm_deployment_5.html', vcenter=session['vcenter'], datacenter=session['datacenter'], cluster=session['cluster'], template=session['template'], folder=session['folder'], vlan=session['vlan'], name=session['name'], memory=memory, cpu=session['cpu'], disk=disks, ip=session['ip'], netmask=session['netmask'], gateway=session['gateway'], datastoreCluster=session['datastore_cluster']) 

@app.route('/vmloading', methods=['GET', 'POST'])
def vmloading():

    return render_template('vmloading.html') 
    
@app.route('/vmcreated', methods=['GET'])
def vmcreated():
    disks = ''

    for disk in session['disks']:
      disks = disks + str(disk) + 'GB, '

    disks = disks[:-2]

    memory = str(session['memory']) + ' GB'

    return render_template('vmcreated.html', vcenter=session['vcenter'], datacenter=session['datacenter'], cluster=session['cluster'], template=session['template'], folder=session['folder'], vlan=session['vlan'], name=session['name'], memory=memory, cpu=session['cpu'], disk=disks, ip=session['ip'], netmask=session['netmask'], gateway=session['gateway'], datastoreCluster=session['datastore_cluster']) 
    
@app.route('/vmfailed', methods=['GET'])
def vmfailed():

    return render_template('vmfailed.html', log_message=session['log_message']) 
    
@app.route('/datacenter/<vcenter_name>')
def datacenterbyvcenter(vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT datacentername FROM datacenter WHERE vcenterName = %s", [vcenter_name])
    datacenters = cur.fetchall()
    datacenterArray = []
    
    for row in datacenters:
        datacenterArray.append(row[0])
    datacenterArray.sort()
    return jsonify({'datacenters': datacenterArray})
    
@app.route('/template/<vcenter_name>')
def templatebyvcenter(vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT templateName FROM template WHERE vcenterName = %s", [vcenter_name])
    templates = cur.fetchall()
    templateArray = []
    for row in templates:
        templateArray.append(row[0])
    templateArray.sort()
    return jsonify({'templates': templateArray})
    
@app.route('/folder/<datacenter_name>/<vcenter_name>')
def folderbydatacenter(datacenter_name, vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT folderName FROM folder WHERE datacenterName = %s AND vcenterName = %s", [datacenter_name, vcenter_name])
    folders = cur.fetchall()
    folderArray = []
    for row in folders:
        folderArray.append(row[0])
    folderArray.sort()
    return jsonify({'folders': folderArray})

@app.route('/cluster/<datacenter_name>/<vcenter_name>')
def clusterbydatacenter(datacenter_name, vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT clusterName FROM cluster WHERE datacenterName = %s AND vcenterName = %s", [datacenter_name, vcenter_name])
    clusters = cur.fetchall()
    clusterArray = []
    for row in clusters:
        clusterArray.append(row[0])
    clusterArray.sort()
    return jsonify({'clusters': clusterArray})

@app.route('/datastoreCluster/<cluster_name>/<vcenter_name>')
def datastoreclusterbycluster(cluster_name, vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT datastoreClusterName FROM datastorecluster WHERE clusterName = %s AND vcenterName = %s", [cluster_name, vcenter_name])
    datastoreClusters = cur.fetchall()
    datastoreClusterArray = []
    for row in datastoreClusters:
        datastoreClusterArray.append(row[0])
    return jsonify({'datastoreClusters': datastoreClusterArray})

@app.route('/vlan/<cluster_name>/<vcenter_name>')
def vlanbycluster(cluster_name, vcenter_name):

    cur = mysql.connection.cursor()
    cur.execute("SELECT vlanName FROM vlan WHERE dswitchName IN (SELECT dswitchName FROM host_dswitch WHERE hostName IN (SELECT hostName FROM host_cluster WHERE vcenterName = %s AND clusterName = %s))", [vcenter_name, cluster_name])
    vlans = cur.fetchall()
    vlanArray = []
    for row in vlans:
        vlanArray.append(row[0])
    vlanArray.sort()
    return jsonify({'vlans': vlanArray})
    
@app.route('/menu', methods =['GET', 'POST'])
def menu():
    if 'username' in session:
        username = session['username']
    else:
        username = None  
    if request.method == "POST":
      cur = mysql.connection.cursor()
      cur.execute("SELECT userRole FROM user WHERE userName = %s", [session['username']])
      role = cur.fetchone()[0]

      if 'vm-deployment-button' in request.form and role == "ALL":
        return redirect(url_for('vm_deployment_1')) 
      #elif remaining buttons
      else:
        return redirect(url_for('menu'))
      
    return render_template('deployment.html',username=username)

@app.route('/', methods =['GET', 'POST'])
def loginpage():
    if request.method == "POST":
      cur = mysql.connection.cursor()
      cur.execute("""SELECT EXISTS(
                      SELECT 1
                      FROM user
                      WHERE userName = %s)
                      """, [request.form['username']])

      exists = cur.fetchone()[0]
      
      session['username'] = request.form['username']

      if exists:
        print(session['username'] + ": Authorized")
      else:
        print(session['username'] + ": Not authorized")
        return redirect(url_for('loginpage'))

      result = ldap_authentication(session['username'], request.form['password'])

      return redirect(url_for(result))
    return render_template('loginpage.html')
   
@app.before_request
def ensure_logged_in():
   if request.endpoint not in ('loginpage', 'static') and 'username' not in session:
       return redirect(url_for('loginpage'))
     
if __name__ == '__main__':
    PREFERRED_URL_SCHEME = 'https'
    app.secret_key = 'super secret key'
    app.run(host='0.0.0.0', port='0000')