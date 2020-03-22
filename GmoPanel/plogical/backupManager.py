#!/usr/bin/env python3

import argparse
import os
import sys, shutil
from shutil import make_archive
import pathlib
from datetime import date, datetime
import re
import pymysql
import django
import tarfile
sys.path.append('/opt/scripts_py/GmoPanel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GmoPanel.settings")
django.setup()
from plogical.phpManager import execute, execute_outputfile

class backupManager():

    def __init__(self, argv = None):
        self.provi = argv
        self.log = '/home/kusanagi/'+argv+'/log/backup.log'
        self.pwrd = self.get_root_pass()

    def append_log(self, log, message):
        f = open(log, "a+")
        today = datetime.now()
        f.write("%s %s \n" % (today.strftime("%Y-%m-%d %H:%M:%S"), message))
        f.close()

    def get_root_pass(self):
        pwrd = None
        try:
            with open("/root/.my.cnf") as fp: lines = fp.read().splitlines()
            for line in lines:
                grep = re.findall(r'password', line)
                if grep:
                    pwrd = line.split('"')[1]
        except BaseException:
            return False
        return pwrd

    def get_db_name(self):
        try:
            db = pymysql.connect("localhost", "root", self.pwrd, "secure_vps")
            cursor = db.cursor()
            cursor.execute("select id,db_name from provision where provision_name='%s'" % self.provi)
            data = cursor.fetchone()
            db.close()
            return data
        except pymysql.err.OperationalError as err:
            print(' An error has occurred \n', err)
        except pymysql.err.InternalError as err:
            print(' An error has occurred \n', err)

    def backup_db(self):

        data = self.get_db_name()
        print(data)
        db_name = data[1]
        try:
            sqldir = '/home/kusanagi/' + self.provi + '/sql_backup/'
            p = pathlib.Path(sqldir)
            if not p.exists():
                p.mkdir(mode=0o755, parents=True, exist_ok=True)
                shutil.chown(sqldir, 'kusanagi', 'kusanagi')
        except BaseException as error:
            print(error)

        mess = 'Backed up database ' + db_name
        self.append_log(self.log, mess)

        cmd = 'mysqldump --single-transaction -p' + self.pwrd + ' --databases ' + db_name + ' | gzip > ' + sqldir + db_name + '.sql.gz'
        execute_outputfile(cmd, self.log)

    def update_backup_record(self, backup_type, result):

        data = self.get_db_name()
        provi_id = data[0]

        db = pymysql.connect("localhost", "root", self.pwrd, "secure_vps")
        cursor = db.cursor()
        cursor.execute(
            "select id from logs where provision_id=%d and status=0 and backup_type=%d" % (provi_id, backup_type))
        res = cursor.fetchone()
        record_id = res[0]

        if result:
            cursor.execute(
                "update logs set status=1,message='Done' where provision_id=%d and id=%d" % (provi_id, record_id))
        else:
            cursor.execute("update logs set status=-1,message='Failed. See %s' where provision_id=%d and id=%d" % (
            self.log, provi_id, record_id))

        db.commit()
        db.close()

    def compress_provision_dir(self, chdir=''):
        date = datetime.now()
        today = date.strftime("%Y-%m-%d")
        if chdir:
            tarname = chdir + self.provi + '.' + today
        else:
            tarname = '/home/kusanagi/backup/' + self.provi + '.' + today
        source_dir = '/home/kusanagi/' + self.provi
        shutil.make_archive(tarname, "gztar", source_dir)
        return tarname

    def local_backup(self):
        self.append_log(self.log, '--- Local backup')
        self.backup_db()
        tarname = self.compress_provision_dir()
        tar_file = pathlib.Path(tarname + '.tar.gz')
        if tar_file.exists():
            self.update_backup_record(0, 1)
            return {'status': 1, 'msg': 'Backup completed successfully'}
        else:
            self.update_backup_record(0, 0)
            return {'status': 0, 'msg': 'Not found backed up file'}

    def check_ssh_conn(self, remote_user, remote_host, remote_port, remote_pass):
        cmd = 'sshpass -p "' + remote_pass + '" ssh -o StrictHostKeyChecking=no -p ' + remote_port + ' -q ' + remote_user + '@' + remote_host + ' exit;echo $?'
        res = execute(cmd)
        if int(res) == 0:
            # print('Connect OK \n')
            pass
        else:
            self.append_log(self.log, 'Remote connection failed. Can not issue remote backup')
            self.update_backup_record(1, 0)
            return {'status': 0, 'msg': 'Remote connection failed'}
            sys.exit(1)

    def remote_backup(self, remote_user, remote_host, remote_port, remote_pass, remote_dest):

        self.append_log(self.log, '--- Remote backup')
        self.check_ssh_conn(remote_user, remote_host, remote_port, remote_pass)
        self.backup_db()
        tarname = self.compress_provision_dir('/home/kusanagi/')

        conf_ssh = '/etc/ssh/ssh_config'
        with open(conf_ssh) as fp:
            lines = fp.read().splitlines()
        for line in lines:
            grep = re.findall(remote_host, line)
            if grep:
                break
        if not grep:
            # configure stricthostkey ssh
            f = open(conf_ssh, "a+")
            f.write('Host %s\n\tStrictHostKeyChecking no\n' % remote_host)
            f.close()

        cmd = 'sshpass -p "' + remote_pass + '" rsync --remove-source-files -azhe \'ssh -p' + remote_port + '\' ' + tarname + '.tar.gz ' + remote_user + '@' + remote_host + ':' + remote_dest + ' 2>> ' + self.log + ' ; echo $?'
        res = execute(cmd)
        if int(res) == 0:
            self.update_backup_record(1, 1)
            return {'status': 1, 'msq': 'Backup completed successfully'}
        else:
            self.update_backup_record(1, 0)
            return {'status': 0, 'msg': 'Check %s for more details' % self.log}

    def drive_backup(self, drive_dir):

        self.append_log(self.log, '--- Backup to Google Drive')
        self.backup_db()
        tarname = self.compress_provision_dir('/home/kusanagi/')
        cmd = 'rclone copy ' + tarname + '.tar.gz GGD1:' + drive_dir + ' 2>> ' + self.log + ' ; echo $?'
        res = execute(cmd)
        if int(res) == 0:
            self.update_backup_record(2, 1)
            return {'status': 1, 'msq': 'Backup completed successfully'}
        else:
            self.update_backup_record(2, 0)
            return {'status': 0, 'msg': 'Check %s for more details' % self.log}
        os.remove(tarname + '.tar.gz')

