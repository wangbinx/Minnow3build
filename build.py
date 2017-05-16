#!/usr/bin/python
#This script for Minnow3 image auto build
import os
import sys
import subprocess
import shutil
import time
import filecmp

#Define path
root_path=os.getcwd()
edk_path=os.path.join(root_path,'edk2-platforms')
Image_path=os.path.join(root_path,'Image')
log_path=os.path.join(Image_path,'log')
email_path=os.path.join(root_path,'email')
backup_path=os.path.join(root_path,'backupfile')
backup_basetools=os.path.join(backup_path,'Win32')
backup_FPS=os.path.join(backup_path,'ApolloLakeFspBinPkg')
backup_UNDI=os.path.join(backup_path,'I210PcieUndiDxe')
backup_nasm=os.path.join(backup_path,'nasm')
backup_Iasl=os.path.join(backup_path,'Iasl')
backup_openssl=os.path.join(backup_path,'openssl-1.0.2g')
backup_IFWI=os.path.join(backup_path,'IFWI')
basetools_path=os.path.join(edk_path,'BaseTools','Bin','Win32')
FSP_path=os.path.join(edk_path,'Silicon','BroxtonSoC','BroxtonFspPkg','ApolloLakeFspBinPkg')
UNDI_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Binaries','UNDI','I210PcieUndiDxe')
nasm_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Tools','nasm')
Iasl_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Tools','Iasl')
openssl_path=os.path.join(edk_path,'Core','CryptoPkg','Library','OpensslLib','openssl-1.0.2g')
IFWI_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Binaries','IFWI')
build_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Tools','Stitch')

#Image build values
build_bat = 'BuildBIOS.bat'
vs_version = 'VS15'
broxton = 'Broxton'


#edk2-platforms download path
ssh_edk= "git@github.com:tianocore/edk2-platforms.git -b devel-MinnowBoard3"
https_edk= "https://github.com/tianocore/edk2-platforms.git -b devel-MinnowBoard3"

#edk2-BaseTools-win32 download path, not used because already backup
ssh_basetool= "git@github.com:tianocore/edk2-BaseTools-win32.git"
https_basetool= "https://github.com/tianocore/edk2-BaseTools-win32.git"

#Check platform
def check_platform():
	if sys.platform == "win32":
		return "windows"
	elif sys.platform == "linux2":
		return "linux"
	else:
		print "Script only support on Windows and Linux"
		exit()

#Check backup floder exists
def check_floder(path):
	platform = check_platform()
	if platform == "windows":
		try:
			if os.path.exists(path):
				print "%s exist --PASS" %path
				pass
			else:
				print "%s lost --Failed" %path
				exit()
		except Exception, e:
			print e
			exit()
	elif platform =="linux":
		print "Waiting linux support Build Script"
		exit()
		

#Check repository exist, if exist, will delete
#Download repository from Github, repo is the repository name or path, ssh/https is the ssh/https link for repository
def download_repository(repo,ssh,https):
	try:
		platform = check_platform()
		if platform == "windows":
			if os.path.exists(repo):
				os.system('rmdir /S /Q %s' %repo)
				if os.path.exists(repo):
					print "Delete the floder %s failed, please delete the floder in %s before run the script" %(repo,root_path)
					exit()
				else:
					pass
			else:
				pass
		elif platform == "linux":
			if os.path.exists(repo):
				shutil.rmtree(repo)
				if os.path.exists(repo):
					print "Delete the floder %s failed, please delete the floder in root_path" %(repo,root_path)
					exit()
				else:
					pass
			else:
				pass
		#Download from Github
		try:
			DL1 = subprocess.check_call("git clone --depth=1 %s" %ssh,shell=True)
			if DL1 == 0:
				print "Download from %s success --PASS" %ssh
		except subprocess.CalledProcessError:
			print "Download from %s failed, try %s" %(ssh,https)
			try:
				DL2 = subprocess.check_call("git clone --depth=1 %s" %https,shell=True)
				if DL2 ==0:
					print "Download from %s success --PASS" %https
			except Exception, e:
				print e
				exit()
	except Exception, e:
		print e
		exit()

# check environment configuration for run
def check_install():
	if check_platform() == "windows":
		edk2_check = os.path.exists(edk_path)
		basetools_check = os.path.exists(basetools_path)
		FSP_check = os.path.exists(FSP_path)
		UNDI_check = os.path.exists(UNDI_path)
		nasm_check = os.path.exists(nasm_path)
		Iasl_check = os.path.exists(Iasl_path)
		openssl_check = os.path.exists(openssl_path)
		IFWI_check = os.path.exists(IFWI_path)
		try:
			if edk2_check and basetools_check and FSP_check and UNDI_check and nasm_check and Iasl_check and openssl_check and IFWI_check == True:
				print "Check build environment configuration --PASS"
			else:
				print "Build environment configuration may damage, please select configure environment and run the script"
		except Exception, e:
			print e
			exit()
	elif check_platform() == "linux":
		print "Waiting linux support Build Script"
#Copy file to specified path
def copy_to_path(orgin_path,specified_path):
	try:
		if os.path.exists(specified_path):
			try:
				shutil.rmtree(specified_path)
				print "Delete floder %s" %specified_path
				shutil.copytree(orgin_path,specified_path)
				print "Copy file %s to %s successful --PASS" %(orgin_path,specified_path)
			except Exception, e:
				print e
				exit()
		else:
			shutil.copytree(orgin_path,specified_path)
			print "Copy file %s to %s successful --PASS" %(orgin_path,specified_path)
	except Exception, e:
		print e
		exit()

#compare version change
def ver_comp(repo_path,log_path):
	repo_log= os.path.join(repo_path,'version.log')
	try:
		if os.path.exists(repo_path):
			if os.path.exists(log_path):
				try:
					os.chdir(repo_path)
					subprocess.check_call('git log -1 > version.log',shell=True)
					os.chdir(log_path)
					if os.path.exists('version.log'):
						os.remove('version.log')
					shutil.move(repo_log,log_path)
				except Exception, e:
					print e
					exit()
			else:
				os.makedirs(log_path)
				ver_comp(repo_path,log_path)
			os.chdir(log_path)
			if os.path.exists('version.log.bak'):
				result = filecmp.cmp('version.log.bak','version.log')
				if result == False:
					print "Detect version has update, will start build process"
					if os.path.exists('version.log.bak'):
						os.remove('version.log.bak')
						shutil.copy('version.log','version.log.bak')
					os.chdir(root_path)
					return "update"
				else:
					print "Detect version has not update, still run script to detect change..."
					return "same"
			else:
				print "No old version be detected, it is the first time to build image."
				return "first"
	except Exception, e:
			print e

#Configuration build environment
def update_version():
	try:
		#download_repository('edk2-platforms',ssh_edk,https_edk)
		copy_to_path(backup_FPS,FSP_path)
		copy_to_path(backup_IFWI,IFWI_path)
		copy_to_path(backup_Iasl,Iasl_path)
		copy_to_path(backup_UNDI,UNDI_path)
		copy_to_path(backup_basetools,basetools_path)
		copy_to_path(backup_nasm,nasm_path)
		copy_to_path(backup_openssl,openssl_path)
		print "Build environment configure successful --PASS"
	except Exception, e:
		print e
#Image build
def build_image(build_bat,vs_version,arch,broxton,image_type):
	print "Begin build image %s %s" %(arch,image_type)
	try:
		os.chdir(edk_path)
		#log=open('%s%s.log'%(arch,image_type),'w+')
		#__origin__ = sys.stdout
		#sys.stdout=log
		#print "Image build test"
		build=subprocess.check_call('%s /%s /%s %s %s > %s%s.log' %(build_bat,vs_version,arch,broxton,image_type,arch,image_type),shell=True)
		#sys.stdout = __origin__
		#log.close()
		os.chdir(log_path)
		if os.path.exists('%s%s.log'%(arch,image_type)):
			os.remove('%s%s.log'%(arch,image_type))
			if os.path.exists('%s%s.log'%(arch,image_type)):
				print "Remove old log file failed"
			else:
				print "Remove old log file --PASS"
		os.chdir(edk_path)
		shutil.move('%s%s.log'%(arch,image_type),log_path)
	except Exception, e:
			print e

#Always detect version change
def detect_version():
	try:
		download_repository('edk2-platforms',ssh_edk,https_edk)
		de_ver = ver_comp(edk_path,log_path)
		return de_ver
	except Exception, e:
		print e


#If version update, will build image, else will pause 30min and detect again
def keep_update():
	version= detect_version()
	if version == 'same':
		print "Script will detect the version after 8H, press Ctrl+C to stop the script"
		time.sleep(28800)
		keep_update()
	elif version == 'update':
		update_version()
		build_image(build_bat,vs_version,'IA32',broxton,'Release')
		build_image(build_bat,vs_version,'IA32',broxton,'Debug')
		build_image(build_bat,vs_version,'x64',broxton,'Release')
		build_image(build_bat,vs_version,'x64',broxton,'Debug')
		#print "Build image begin **************************************** "
		search(build_path,'MINNOWV3.')
		build_result()
		keep_update()
	elif version== 'first':
		update_version()
		os.chdir(log_path)
		shutil.copy('version.log','version.log.bak')
		#print "Build image begin **************************************** "
		build_image(build_bat,vs_version,'IA32',broxton,'Release')
		build_image(build_bat,vs_version,'IA32',broxton,'Debug')
		build_image(build_bat,vs_version,'x64',broxton,'Release')
		build_image(build_bat,vs_version,'x64',broxton,'Debug')
		search(build_path,'MINNOWV3.')
		build_result()
		os.chdir(log_path)
		shutil.copy('version.log','version.log.bak')
		keep_update()

#copy image file to Image path
def search(path,key_w):
	try:
		#date=time.strftime('%Y%m%d')
		#date_image_path=os.path.join(Image_path,date)
		#os.makedirs(date_image_path)
		for name in os.listdir(path):
			filename = os.path.join(path,name)
			if os.path.isfile(filename) and key_w in filename:
				print "%s Image file found" %name
				os.chdir(Image_path)
				if os.path.exists(name):
					move=raw_input("Image file %s already exist, do you want to override(y/n/all):" %name)
					if move =="y":
						try:
							os.remove(name)
							shutil.move(filename,Image_path)
							print "%s move success --PASS" %name
						except Exception,e:
							print e
					else:
						print "%s not move for user selection" %name
				else:
					shutil.move(filename,Image_path)
					print "%s move success --PASS" %name
	except Exception, e:
		print e
#check log file for report build result
def build_result():
	try:
		build_pass =[]
		message = "Build_IFWI is finished"
		body = os.path.join(email_path,'__Email_Body_File.txt')
		for path,dir,logfile in os.walk(log_path,topdown=True,onerror=None, followlinks=False):
			os.chdir(path)
			for name in logfile:
				log = open(name,'r')
				for result in log.readlines():
					if message in result:
						build_pass.append(name[:-4])
		if os.path.exists(body):
			os.remove(body)
		with open(body,'wb')as mail_body:
			mail_body.write("Build Pass:\n\r")
			mail_body.write(str(build_pass))
			mail_body.close()
		print "Add build result to mail body--pass"
		os.chdir(email_path)
		subprocess.check_call('SendReport.bat',shell=True)
	except Exception, e:
		print e

#Script begining
print "***************Script begin for Minnow3 Image auto Build*************"
print """
If you want to install the build environment and run, please input Yes
If the environment has already configuration, please input No"""
select_script=raw_input("Input(y/n):")
if select_script in ['y','yes','Yes','Y','YES']:
#check backupfile floder and email exist
	try:
		check_floder(backup_path)
		check_floder(email_path)
#Configure Build environment
		keep_update()
	except Exception, e:
		print e
elif select_script in ['n','N','No','NO','no']:
	try:
		check_install()
		keep_update()
	except Exception, e:
		print e
else:
	print "Input ERROR"
print "Last line of Script"