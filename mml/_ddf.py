#!/bin/python3
from collections import UserDict

class diva_db_file(UserDict):
    def __init__(self,file,mode="r"):
        self.filename=file
        self.file=open(file,mode,encoding='utf_8_sig')
        self.data={}


    def readlines(self):
        commit_num=0
        for line in self.file.readlines():
            line=line.rstrip("\n")
            if line.startswith("#"):
                key="commit%05d"%commit_num
                commit_num+=1
                self.data.update({key:line})
                continue
            
            line=line.split("=")
            ll=len(line)
            if ll==2:
                self.data.update({line[0]:line[1]})
            elif ll==1:
                key="commit%05d"%commit_num
                commit_num+=1
                self.data.update({key:line[0]})
            elif ll>2:
                key=line[0]
                value="=".join(line[1:])
                self.data.update({key:value})
        return self.data
    
    def write_file(self,filename):
        out_file=open(filename,"w",encoding='utf_8_sig')
        for line in self.data:
            if line.startswith("commit"):
                line_str=self.data[line]+"\n"
            else:
                line_str="%s=%s\n"%(line,self.data[line])
            out_file.write(line_str)
        out_file.flush()


    def __del__(self):
        self.file.close()

if __name__=="__main__":
    pass
