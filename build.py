#!/usr/bin/python
#This script for Minnow3 image auto build
## Add type to script need add below information
## 1.Add the type to controller excel, please follow the format, don't change the merge cell format
## 2.Add key_msg which the information on BIOS file name to misc()
## 3.Add Build command parameter to command_dict on command()
## 4.Add to self.dict:{Logfilename[0]:'xxx',VS2015_image_filename[0:-1]:'xxx',GCC_image_filename[0:-1]:'xxx'} on class result
## 5.Add html table to html_model, to create result report and email
##
import os,platform,subprocess,filecmp,re
import stat,shutil,zipfile, xlrd
import time,datetime,logging
import smtplib
from optparse import OptionParser
from string import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#Define path
root_path=os.getcwd()
edk_path=os.path.join(root_path,'edk2-platforms')
tmp=os.path.join(root_path,'tmp')
M_Readme=os.path.join(root_path,'Readme','Minnow3.txt')
AUR_Readme=os.path.join(root_path,'Readme','Aurora Glacier.txt')
MT_Readme=os.path.join(root_path,'Readme','Minnow3 Module.txt')
LH_Readme=os.path.join(root_path,'Readme','Leaf Hill.txt')
Minnow3_Readme=os.path.join(tmp,'Readme_Minnow3.txt')
AuroraGlacier_Readme=os.path.join(tmp,'Readme_Aurora Glacier.txt')
Minnow3Module_Readme=os.path.join(tmp,'Readme_Minnow3 Module.txt')
LeafHill_Readme=os.path.join(tmp,'Readme_Leaf Hill.txt')
html_model=os.path.join(root_path,'Readme','result_model.html')
image_build_path=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','Common','Tools','Stitch')
Firmwareupdate_path=os.path.join(root_path,'Build','BroxtonPlatformPkg')
network_path=os.path.join('\\\shwde9524','Backup_IntelAtomE3900')

#mount network share path to ubuntu path
network_GCC=os.path.join('/media','Backup_IntelAtomE3900')

#Image share location
mail_share_path = "\\\shwde9524\Backup_IntelAtomE3900\\"


# Set Image file size to determine the build result
Image_size = '8M'

#Email for result
sender = 'binx.a.wang@intel.com'
receiver = ['weix.b.sun@intel.com','binx.a.wang@intel.com','linglix.ji@intel.com','yanyanx.zhang@intel.com','yunhuax.feng@intel.com']
Cc=['yonghong.zhu@intel.com','david.wei@intel.com','zailiang.sun@intel.com','yi.qian@intel.com']

def sys():
	if platform.system() == "Windows":
		return True
	elif platform.system() == "Linux":
		return False
	else:
		logger.error("Not support")
		exit()
# Different between windows and linux
#'key_msg': Information on BIOS file name
def misc():
	if sys():
		misc={
		'key_msg_in_log':"Build_IFWI is finished",	
		'tool':'VS2015','Minnow3':{'key_msg':'MINNOW3'},'Benson Glacier':{'key_msg':'BENSONV'},'Minnow3 Module':{'key_msg':'M3MODUL'},'Leaf Hill':{'key_msg':'LEAFHIL'},'Aurora Glacier':{'key_msg':'AURORAV'},'UP2':{'key_msg':'UPBOARD'}}
	else:
		misc={
		'key_msg_in_log':"FV Space Information",
		'tool':'GCC','Minnow3':{'key_msg':'MNW3'},'Benson Glacier':{'key_msg':'BEN1'},'Minnow3 Module':{'key_msg':'M3MO'},'Leaf Hill':{'key_msg':'LEAF'},'Aurora Glacier':{'key_msg':'AUR'},'UP2':{'key_msg':'UPBO'}}
	return misc

#Clasee for repository
#Modify the link if chaged
#Download, delete, compare update and create version folder
class repository:
	ssh_edk2platform= "git@github.com:tianocore/edk2-platforms.git -b devel-IntelAtomProcessorE3900"
	https_edk2platform= "https://github.com/tianocore/edk2-platforms.git -b devel-IntelAtomProcessorE3900"
	
	ssh_edk2 = "git@github.com:tianocore/edk2.git -b vUDK2018"
	https_edk2 = "https://github.com/tianocore/edk2.git -b vUDK2018"
	
	root =os.getcwd() #recoder the path
	def __init__(self,ver_log_path,https,ssh=None):
		self.ver_log_path=ver_log_path
		self.ssh=ssh
		self.https=https
		self.repo=self.https.split('/')[-1].split('.')[0]
		
	def delete(self):
		try:
			for path,dir,file in os.walk(self.repo,topdown=True,onerror=None, followlinks=False):
				for k in file:
					filename=os.path.join(path,k)
					if os.path.isfile(filename):
						os.chmod(filename,stat.S_IRWXU) #change file mode to delete the repository
			time.sleep(5)
			if os.path.exists(self.repo):
				logger.info('%s repository already exist, delete the repository'%self.repo)
				shutil.rmtree(self.repo)
				logger.info("Delete exist repository %s success" %self.repo)
		except Exception,e:
			logger.error(str(e))
			time.sleep(20)
			self.delete()
		
	def download(self):
		self.delete()
		try:
			logger.info('Downloading repository %s'%self.repo)
			DL1 = subprocess.check_call("git clone --depth=1 %s" %self.https,shell=True)
			if DL1 == 0:
				logger.info("Download from %s success --PASS" %self.https)
				return True
		except subprocess.CalledProcessError:
			if self.ssh != None:
				logger.warning("Download from %s failed, try %s" %(self.https,self.ssh))
				DL2 = subprocess.check_call("git clone --depth=1 %s" %self.ssh,shell=True)
				if DL2 ==0:
					logger.info("Download from %s success --PASS" %self.ssh)
					return True
			else:
				logger.error("Download repository %s Fail" %self.repo)
				exit()
	#compare to detect code update
	#True for update or never build, False for not update
	#If set Force_Build_Switch to 1, will build no matter code update or not
	def compare(self):
		version=os.path.join(self.ver_log_path,'version.log')
		bak=os.path.join(self.ver_log_path,'version.log.bak')
		if not os.path.exists(self.ver_log_path):
			os.mkdir(self.ver_log_path)
		os.chdir(self.repo)
		subprocess.check_call('git log -1 > version.log',shell=True)
		shutil.copy('version.log',self.ver_log_path)
		os.chdir(self.ver_log_path)
		if os.path.exists(bak):
			comp=filecmp.cmp(version,bak)
			os.chdir(repository.root)
			if comp == False:
				logger.info("Code version has update")
				shutil.copy(version,bak)
				return True
			else:
				logger.info("Code version not update")
				return False
		else:
			logger.info("No old version be detected")
			os.chdir(repository.root)
			shutil.copy(version,bak)
			return True
	
	#create version folder and return
	def verpath(self):
		global version_info,verlog
		verlog=os.path.join(self.ver_log_path,'version.log')
		try:
			fo=open(verlog)
		except Exception,e:
			logger.error("Open %s failed" %verlog+str(e))
		line=fo.readline()
		if 'commit' in line:
			version_info=line[7:47]
			path = os.path.join(root_path,'Image',line[7:15])
		else:
			version_info='No Version'
			path = os.path.join(root_path,'Image','No Version')
		if os.path.exists(path):
			shutil.rmtree(path)
			time.sleep(3)
		os.makedirs(path)
		fo.close()
		return path
	
	def allstep(self):
		global Force_Build_Switch
		self.download()
		if Force_Build_Switch == 0:
			return self.compare()
		elif Force_Build_Switch == 1:
			logger.info("Force Build Switch set to 1, begin build image")
			self.compare()
			Force_Build_Switch = 0
			return True
			
	def edk2_openssl(self):
		redk2 = self.download()
		#if redk2:
			#ropenssl = subprocess.check_call("cd edk2 && git submodule update --init --recursive",shell=True)
			#if ropenssl == 0:
			#	logger.info("Init submodule Openssl finish")
			#	if not sys():
			#		subprocess.check_call("chmod -R 777 %s"%self.repo,shell= True)
			#	return True
			#else:
			#	logger.error("Init submodule Openssl failed")
			#	exit()
			
#class for svn update
#change the link, username and password		
class svn:
	user = "sys_tianobui"
	password = "IB5J6eaRQvE/sdE4g774LY97rRnVnA7L7i71rzatNpuPKnKQ="
	link = "https://ssvn.intel.com:80/ssg/csd/tiano/tianoad/trunk/Platforms/MinnowBoard3/Binaries/devel-IntelAtomProcessorE3900"
	
	def __init__(self, user, passwd, link):
		self.user=user
		self.passwd=passwd
		self.link=link
		self.command = "--non-interactive --no-auth-cache --trust-server-cert --username %s --password %s"%(self.user,self.passwd)
		self.svnfolder=self.link.split('/')[-1]
		
	def download(self):
		try:
			if os.path.exists(self.svnfolder):
				logger.info("Update necessary files from SVN")
				svn_result = subprocess.check_call("svn update %s %s" %(self.svnfolder,self.command),shell=True)
			else:
				logger.info("Download necessary files form SVN")
				svn_result = subprocess.check_call("svn checkout %s %s" %(self.link,self.command),shell=True)
			return svn_result
		except Exception, e:
			logger.error(e)
			time.sleep(10)
			self.download()
			return 0
	
	#Copy file to config build environment
	def copy(self):
		if not self.download() == 0:
			logger.error('Download or Update necessary file from SVN failed')
			exit()
		else:
			logger.info('Start configure build environment')
			try:
				if sys():
					subprocess.check_call('xcopy /Q /E /Y %s %s' %(self.svnfolder,root_path), shell=True)
				else:
					subprocess.check_call('cp -r %s/* %s' %(self.svnfolder,root_path), shell=True)
				logger.info('Configure finish')
			except Exception, e:
				logger.error("Configure build environment failed:"+str(e))
				exit()

#Class for zip source code and unzip
#Will zip file to Source\
class zip_source_file:
	root = os.getcwd()
	def __init__(self,filename,zipdir,ziptarget):
		global Source_path
		self.zipdir=zipdir
		self.zipfilename="%s.zip"%filename
		self.ziptarget=os.path.join(ziptarget,'Source')
		self.source= os.path.join(self.ziptarget,self.zipfilename)
		Source_path=self.ziptarget
				
	def zip(self):
		if sys():
			filelist = []
			for dir in self.zipdir:
				if os.path.isfile(dir):
					filelist.append(dir)
				else:
					for path, dirs, files in os.walk(dir):
						for name in files:
							filelist.append(os.path.join(path, name))
			try:
				logger.info("Zipping %s to save source code..." %self.zipfilename)
				zf = zipfile.ZipFile(self.zipfilename, "w", zipfile.zlib.DEFLATED)
				for file in filelist:
					zf.write(file)
				zf.close()
				logger.info('zip %s success'%self.zipfilename)
			except Exception,e:
				logger.error("Zip failed:"+str(e))
		else:
			zipcommand = 'zip -ry %s '%self.zipfilename
			for dir in self.zipdir:
				zipcommand += dir+' '
			os.system(zipcommand.strip())
		if os.path.exists(self.ziptarget):
			shutil.rmtree(self.ziptarget)
		os.makedirs(self.ziptarget)
		shutil.move(self.zipfilename,self.ziptarget)
			
	def unzip(self):
		os.chdir(zip_source_file.root)
		if os.path.exists(self.zipdir[0]):
				repository(tmp,repository.https_edk2platform,repository.ssh_edk2platform).delete()
				repository(tmp,repository.https_edk2,repository.ssh_edk2).delete()
		if not os.path.exists(self.source):
			logger.error('%s file not exist'%self.source)
		try:
			logger.info('start unzip %s file'%self.source)
			unzip=zipfile.ZipFile(self.source,'r')
			for file in unzip.namelist():
				unzip.extract(file,root_path)
			unzip.close()
			logger.info('unzip %s success'%self.zipdir)
			if not sys():
				for dir in self.zipdir:
					try:
						subprocess.check_call('chmod -R 777 %s'%dir,shell=True) #Change unzip file mode for execute
					except Exception,e:
						logger.error('Change %s access failed'%dir+str(e))
		except Exception,e:
			logger.error("Unzip failed:"+str(e))

#Class for excel
#Read the excel and return build command
#Please follow the excel format when add
class excel:
	root = os.getcwd()
	if sys():
		xls_file = os.path.join(root,'Readme','controller_win.xlsx')
	else:
		xls_file = os.path.join(root,'Readme','controller_ubuntu.xlsx')
	control_sheet = 'Controller'
	def readxls(self):
		all=[]
		select=[]
		try:
			xls = xlrd.open_workbook(excel.xls_file)
			sh = xls.sheet_by_name(excel.control_sheet)
		except Exception,e:
			logger.error('please makesure sheet %s exist'%(excel.control_sheet)+str(e))
		ncol = sh.ncols
		nrow = sh.nrows
		for i in range(0,nrow):
			for a in range(0, ncol):
				if sh.merged_cells:
					for x in sh.merged_cells:
						if sys():  # Windows format
							if (i in range(x[0],x[1]) and a in range(x[2],x[3])):
								if (x[2],x[3])==(0,1):
									plat=sh.cell_value(x[0],x[2])
								elif (x[2],x[3])==(1,2):
									FAB=sh.cell_value(x[0],x[2])
				else:
					plat=sh.cell_value(i,0)
					FAB=sh.cell_value(i,1)
				value = sh.cell_value(i,a)
				if (value == 'y' or value == 'Y'or value == 'N/A' or value == 'n/a'):
					arch = sh.cell_value(i,2)
					type = sh.cell_value(0,a)
					if (value == 'y' or value == 'Y'):
						selecttd='%s_%s_%s_%s'%(plat,FAB,arch,type)
						select.append(selecttd)
					alltd='%s_%s_%s_%s'%(plat,FAB,arch,type)
					all.append(alltd)
		return (all,select)
		##[u'Minnow3_FAB A_IA32_R', u'Minnow3_FAB A_IA32_D']
	
	#Return command
	#add the para to the command_dict if want to add some type
	def command(self):
		command_dict={
		'Minnow3':'',				'Benson Glacier':'/BG',
		'Minnow3 Module':'/MX',		'Leaf Hill':'/LH',
		'Aurora Glacier':'/AG',		'UP2':'/UP',
		'FAB B':'/B',				'FAB A':'/A',		'FAB D':'/D',		'FAB C':'/C',
		'X64':'/X64',				'IA32':'/IA32',
		'Release':'Release type=normal',	'Debug':'Debug type=normal',
		'Fastboot(R)':'Release type=Fastboot(R)','Source Level Debug':'Debug type=Source Level Debug','Disable flash region access(R)':'Release type=Disable flash region access(R)'}
		xls=self.readxls()
		buildcommand=[]
		logger.info('*'*20+'Below command will Run'+'*'*20)
		for list in xls[1]:
			value=list.split('_')
			Actaul_value = []
			try:
				for key in value:
					if key in command_dict.keys():
						Actaul_value.append(command_dict[key])
				if sys():
					##command format for windows
					##example: BuildBIOS.bat /VS15 /m /A /X64 Broxton Debug type=normal
					command ='BuildBIOS.bat /VS15 /m %s %s %s Broxton %s'%(tuple(Actaul_value))
				else:
					##command format for linux
					##example: /bin/bash ./BuildBIOS.sh /A Debug type=normal
					command ='/bin/bash ./BuildBIOS.sh %s %s %s'%(Actaul_value[0],Actaul_value[1],Actaul_value[3])
				logger.info(command)
				buildcommand.append(command)
			except Exception,e:
				print e
				logger.warning("Some table can't be analyzed")
		logger.info('*'*62)
		return buildcommand,command_dict

#Search file from findpath and copy to targetpath
#the para rule is the regular expression rule
def copy(findpath,targetpath,rule,rename=None):
	findfile =re.compile(rule,re.S)
	if os.path.exists(findpath):
		for path,dir,file in os.walk(findpath,topdown=True,onerror=None, followlinks=False):
			if file != []:
				for z in file:
					full_path = os.path.join(path,z)
					filename = findfile.findall(z)
					if filename:
						if os.path.exists(targetpath):
							if rename != None:
								targetpath=os.path.join(targetpath,rename)
							try:
								shutil.copy(full_path,targetpath)
								logger.info('copy %s to %s success'%(filename[0],targetpath))
							except Exception,e:
								logger.warning('copy %s to %s failed'%(filename[0],targetpath)+str(e))
						else:
							logger.warning('copy %s failed,target path %s not exists'%(filename,targetpath))
	else:
		logger.error("The path %s not exists"%findpath)

#modify file content
#Search keyword, replace the var1 to var2
def modify(filename,keyword,var1,var2,rename=None):
	try:
		f=open(filename,'r+')
		lines = f.readlines()
		f.close()
		if rename == None:
			f=open(filename,'w+')
		else:
			f=open(rename,'w+')
		for line in lines:
			if keyword in line:
				line=line.replace(var1,var2)
			f.write(line)
		f.close()
		logger.info('%s file modify success'%filename)
	except Exception,e:
		logger.error(e)

#Class for Build Image
class build:
	Dscpath=os.path.join(edk_path,'Platform','BroxtonPlatformPkg','PlatformDsc','Defines.dsc')

	def __init__(self,command,analyze_dict):
		##example: BuildBIOS.bat /VS15 /m /A /X64 Broxton Debug type=normal
		##example: /bin/bash ./BuildBIOS.sh /A Debug type=normal
		self.dict1={x:y for y, x in analyze_dict.items()} #reverse the command_dict
		self.command=command.split('type=')[0]
		self.imagetype=command.split('type=')[1] #normal/Fastboot/Source Level Debug
		self.list = self.command.split(' ')
		self.type = self.list[-2] #Debug/Release
		if sys():
			self.FAB=self.list[-5][-1] #A/B
			self.arch = self.list[-4][1:] #X64/IA32
			self.board=self.dict1[self.list[3]]
		else:
			self.FAB =self.list[-3][-1] #A/B
			self.arch = 'X64'
			self.board=self.dict1[self.list[2]]
		self.logformat='%s_%s_%s_%s'%(self.board,self.FAB,self.arch,self.type)
	
	def buildprocess(self):
		logger.info('-'*8+'Begin Build %s %s %s %s %s Image'%(self.board,self.FAB,self.arch,self.type,self.imagetype)+'-'*8)
		logger.info('Build Command: %s'%self.command)
		key_msg=misc()[self.board]['key_msg']
		Image=os.path.join(ver_path,self.board,'FAB %s'%self.FAB,misc()['tool'],'Image')
		Log= os.path.join(ver_path,self.board,'FAB %s'%self.FAB,misc()['tool'],'Log')
		if not (os.path.exists(Image) and os.path.exists(Log)):
				os.makedirs(Image)
				os.makedirs(Log)
		if self.imagetype !='normal':
			Image=os.path.join(Image,self.imagetype)
			Log= os.path.join(Log,self.imagetype)
			if not (os.path.exists(Image) and os.path.exists(Log)):
				os.makedirs(Image)
				os.makedirs(Log)
			if self.imagetype in ['Fastboot(R)','Source Level Debug']:
				Dsc_origin= os.path.join(Image,'Defines_ori.dsc')
				Dsc_special = os.path.join(Image,'Defines_'+self.imagetype+'.dsc')
				shutil.copy(build.Dscpath,Dsc_origin)
				if self.imagetype == 'Fastboot(R)': #Settings for Fastboot
					modify(build.Dscpath,'PERFORMANCE_ENABLE','FALSE','TRUE')
					modify(build.Dscpath,'INTEL_FPDT_ENABLE','TRUE','FALSE')
				elif self.imagetype == 'Source Level Debug': #Settings for Source Level Debug
					modify(build.Dscpath,'SOURCE_DEBUG_ENABLE','FALSE','TRUE')
				shutil.copy(build.Dscpath,Dsc_special)
			elif self.imagetype in ['Disable flash region access(R)']:
				tmpcommand = self.command.split(" ")
				tmpcommand.insert(-4, "/L")
				self.command = " ".join(tmpcommand)
		try:
			pass
			buildimage=subprocess.check_call('%s > "%s.log"'%(self.command,self.logformat),shell=True)
		except Exception,e:
			logger.error('Build Failed:'+str(e))
		copy(image_build_path,Image,'%s.*bin'%key_msg) #move Image file
		try:
			shutil.copy('%s.log'%self.logformat,Log) #move log file
		except Exception,e:
			logger.error('Move log file %s.log failed\n\r'%self.logformat+str(e))
		if 'Release' in self.command and self.imagetype =='normal':
			##If Build Release Image, copy the FirmwareUpdate.efi to Image path
			copy(Firmwareupdate_path,Image,'FirmwareUpdate.efi','FirmwareUpdate%s.efi'%self.arch)
		logger.info('-'*15+'Build finished'+'-'*15)

class result:
	root =os.getcwd()
	def __init__(self,Imagefolder):
		self.folder=Imagefolder
		self.dict={	'Benson Glacier':'BEN', 	'BENSONV':'BEN',	'BEN1':'BEN', 
					'Minnow3':'MIN3',			'MINNOW3':'MIN3',	'MNW3':'MIN3', 
					'Minnow3 Module':'MINT',	'M3MODUL':'MINT',	'M3MO':'MINT',
					'Leaf Hill':'LH',			'LEAFHIL':'LH',		'LEAF':'LH',
					'Aurora Glacier':'AUR',		'AURORAV':'AUR',	'AUR':'AUR',
					'UP2':'UP2',				'UPBOARD':'UP2',	'UPBO':'UP2',
					"FAB A":"A",				"FAB B":"B",		"FAB D":"D",	"FAB C":"C",
					"IA32":"I32",				"X64":"X64",
					"Fastboot(R)":"R_Fastboot(R)",		"Source Level Debug":"D_Source Level Debug",	"Disable flash region access(R)":'R_Disable flash region access(R)',
					"Release":"R_N",					"Debug":"D_N"
					}
	
	#check Image file size 
	def check_size(self):
		size_dict={}
		for path,dir,file in os.walk(self.folder,topdown=True,onerror=None, followlinks=False):
			if file != []:
				for z in file:
					full_path = os.path.join(path,z)
					if os.path.getsize(full_path) == int(Image_size[:-1])*1024*1024:
						file_name= full_path.split(os.path.sep)[-1]
						if sys():
							name_list = file_name.split('.')
							plat = self.dict[name_list[0][0:-1]]
							FAB = name_list[0][-1]
							arch = name_list[1]
							type = name_list[3][0]
						else:
							name_list = file_name.split('_')
							plat = self.dict[name_list[0][0:-1]]
							FAB = name_list[0][-1]
							arch = name_list[1]
							type = name_list[2]
						folder_name = full_path.split(os.path.sep)[-2]
						if folder_name != 'Image':
							size_dict[plat+'_'+FAB+'_'+arch+type+'_'+folder_name] = "Pass"
						else:
							size_dict[plat+'_'+FAB+'_'+arch+type+'_N'] = "Pass"
		#logger.debug("size check rsult"+str(size_dict))
		return size_dict

	#check build log
	def check_log(self):
		log_dict={}
		for path,dir,file in os.walk(self.folder,topdown=True,onerror=None, followlinks=False):
			if file != []:
				for z in file:
					file = os.path.join(path,z)
					result = open(file,'r')
					Content = result.readlines()
					result.close()
					for result in Content:
						if misc()['key_msg_in_log'] in result:
							folder_name = file.split(os.path.sep)[-2]
							file_name = file.split(os.path.sep)[-1]
							name_list = file_name.split('_')
							board=self.dict[name_list[0]]
							FAB = name_list[1]
							arch = name_list[2][0]+name_list[2][-2:]
							type = name_list[3][0]
							if folder_name != 'Log':
								log_dict[board+'_'+FAB+'_'+arch+type+'_'+folder_name] = 'Pass'
							else:
								log_dict[board+'_'+FAB+'_'+arch+type+'_N'] = 'Pass'
		#logger.debug("log info check result"+str(log_dict))
		return log_dict
	
	#analyze the build type from readxls(), and convert to the format which html recognise para
	def analyze(self,data,value):
		dict={}
		for i in data:
			i = i.split('_')
			for list in i:
				if i[0] in self.dict.keys():
					plat = self.dict[i[0]]
					if list in self.dict.keys():
						board= self.dict[i[1]]
						arch  = self.dict[i[2]]
						type = self.dict[i[3]]
			dict[plat+'_'+board+'_'+arch+type] = value
		return dict
	
	#set N/A for not select, and all Green color for pass, Red for fail
	def resultdict(self):
		size=self.check_size()
		log=self.check_log()
		xlsdata=excel().readxls()
		alldata=self.analyze(xlsdata[0],"N/A")
		select=self.analyze(xlsdata[1],' ')
		for key in select.keys():
			if key in size.keys() and key in log.keys():
				if size[key] == 'Pass' and log[key] == 'Pass':
					alldata[key]="<font color ='Green'><b>Pass</b></font>"
			else:
				alldata[key]="<font color='Red'><b>Fail</b></font>"
		return alldata

	#use the html_model the create result page
	#create xxx_result.html for build result
	def html(self):
		os.chdir(result.root)
		dict1 = self._replacespaceinkey(self.resultdict())
		re_header = re.compile('(<html>.*</style>)', re.S)
		re_table = re.compile('(<h4>.*?</table>)', re.S)
		re_footer = re.compile('(</body>.*?</html>)', re.S)
		text=open(html_model,'r').read()
		header=re_header.search(text).group(1)
		footer=re_footer.search(text).group(1)
		if sys():
			table=re_table.findall(text)[0]
		else:
			table=re_table.findall(text)[1]
		htmltext=header+table+footer
		html=Template(htmltext).substitute(**dict1)
		return html,dict1

	def _replacespaceinkey(self, dict):
		dict2 = {}
		flag = False
		for key in list(dict.keys()):
			if " " in key or "(" in key:
				dict2[key.replace(" ", "_").split("(")[0]] = dict[key]
			else:
				dict2[key] = dict[key]
		return dict2

	def write_result(self):
		html,dict1=self.html()
		resulthtml=os.path.join(ver_path,'%s_result.html'%misc()['tool'])
		fo = open(resulthtml,'wb')
		fo.write(html)
		fo.close()
	
	def email(self,sender,receiver,Cc):
		msg = MIMEMultipart()
		log = MIMEText(open('%s' %verlog, 'rb').read())
		log["Content-Type"] = 'application/octet-stream'
		log["Content-Disposition"] = 'attachment; filename="version.log"'
		msg.attach(log)
		if sys():
			msg['Subject'] = 'IntelAtomE3900 Image Build Result -- VS2015 Tool Chain'
		else:
			msg['Subject'] = 'IntelAtomE3900 Image Build Result -- GCC5 Tool Chain'
		remote_path = os.path.join(network_path,ver_path.split(os.path.sep)[-1])
		msg.attach(MIMEText(self.html()[0]+"<br><font size='4'>Image share location:<a href="+remote_path+">"+mail_share_path+ver_path.split(os.path.sep)[-1]+"</a>",'html'))
		msg['From'] = 'Tiano'
		msg['To'] = ';'.join(receiver)
		if  Cc != []:
			msg['Cc'] = ';'.join(Cc)
			receiver = receiver + Cc						   
		try:
			smtpObj = smtplib.SMTP('smtp.intel.com:25')
			smtpObj.sendmail(sender, receiver, msg.as_string())
			logger.info("Build result and log file send success")
		except Exception, e:
			logger.error("Send mail failed:"+str(e))
			
#Upload Image to remote
def upload(local):
	folder_name=local.split(os.path.sep)[-1]
	try:
		if sys():
			remote = os.path.join(network_path,folder_name)
			subprocess.check_call('xcopy /E /Y %s %s\\' %(local,remote), shell=True)
		else:
			remote = os.path.join(network_GCC,folder_name)
			subprocess.check_call('cp -r %s/ %s' %(local,remote), shell=True)
		logger.info("Upload files Pass")
	except Exception, e:
		logger.error("Upload file failed"+str(e))

#record run log
logging.basicConfig(level=logging.DEBUG,
	format='%(levelname)-7s: %(asctime)s  [line:%(lineno)d] %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S',
	filename='Runlog.log',
	filemode='w')
console = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)-7s: %(message)s')
logger=logging.getLogger('')
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)
 
def mainbuild():
	global ver_path
	del_dir=['Build','Conf']
	edk_repo=repository(tmp,repository.https_edk2platform,repository.ssh_edk2platform)
	edk2_repo=repository(tmp,repository.https_edk2,repository.ssh_edk2)
	xls = excel()
	all_command=xls.command()
	if 	edk_repo.allstep() and edk2_repo.download():
		start_time=datetime.datetime.now()
		ver_path=edk_repo.verpath()
		build_result=result(ver_path)
		zipsource=zip_source_file(version_info[0:8],['edk2-platforms','edk2'],ver_path)
		logger.info('Build version:%s'%version_info)
		svn(svn.user,svn.password,svn.link).copy()
		zipsource.zip()
		##create Readme file
		modify(M_Readme,'Version','Version:','Version:'+version_info,Minnow3_Readme)
		modify(AUR_Readme,'Version','Version:','Version:'+version_info,AuroraGlacier_Readme)
		modify(MT_Readme,'Version','Version:','Version:'+version_info,Minnow3Module_Readme)
		modify(LH_Readme,'Version','Version:','Version:'+version_info,LeafHill_Readme)
		copy(tmp,Source_path,'Readme.*') #copy Readme to source folder
		shutil.copy(verlog,Source_path) #copy version.log to source folder
		for command in all_command[0]:
			for dir in del_dir:
				if os.path.exists(dir):
					try:
						shutil.rmtree(dir)
					except Exception, e:
						logger.warning("Remove dir failed, try again. "+str(e))
						shutil.rmtree(dir)
			time.sleep(5)
			os.chdir(edk_path)
			build(command,all_command[1]).buildprocess()
			time.sleep(5)
			zipsource.unzip()
			time.sleep(5)
		logger.info('*'*15+"All build completed"+'*'*15)
		build_result.write_result()
		upload(ver_path)
		build_result.email(sender,receiver,Cc)
		end_time=datetime.datetime.now()
		dtime=end_time-start_time
		logger.info('Total time:%s'%str(dtime)[:-7])
		time.sleep(60)
	else:
		logger.info("No code change, sleep 1 hour, press Ctrl+C to stop the script")
		logger.info("Current time is:"+time.strftime('%Y/%m/%d %H:%M:%S'))
		time.sleep(3600)
	mainbuild()

def main():
	global Force_Build_Switch
	usage="build.py [-s <switch>]"
	parser = OptionParser(usage)
	parser.add_option('-s','--switch',action='store',dest='switch',choices=['0','1'],default=0,help="Force Build switch, will force build Image while run script if set to 1")
	(options,args)=parser.parse_args()
	Force_Build_Switch = int(options.switch)
	logger.info("-"*20+'Minnow3 Image Auto Build'+"-"*20)
	if sys():
		os.system('net use x: %s'%network_path)
	mainbuild()
	
if __name__ == '__main__':
	main()
