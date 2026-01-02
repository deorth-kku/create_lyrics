#!/bin/python3
from collections import UserDict

class diva_db_file(UserDict):
    def __init__(self,file:str=None):
        self.filename=file
        self.data={}
        self.commit=0
        if file:
            self.readlines(file)            

    def addcomment(self,line:str):
        key="commit%05d"%self.commit
        self.commit+=1
        self.data.update({key:line})


    def readlines(self,file:str=None):
        self.commit=0
        if file:
            self.filename=file
        with open(self.filename,"r",encoding='utf_8_sig') as file:
            for line in file.readlines():
                line=line.rstrip("\n")
                if line.startswith("#"):
                    self.addcomment(line)
                    continue
                
                line=line.split("=")
                ll=len(line)
                if ll==2:
                    self.data.update({line[0]:line[1]})
                elif ll==1:
                    self.addcomment(line[0])
                elif ll>2:
                    key=line[0]
                    value="=".join(line[1:])
                    self.data.update({key:value})
        return self.data
    
    def write_file(self,filename:str=None):
        if filename:
            self.filename=filename
        with open(self.filename,"w",encoding='utf_8_sig') as out_file:
            for line in self.data:
                if line.startswith("commit"):
                    line_str="#"+self.data[line]+"\n"
                else:
                    line_str="%s=%s\n"%(line,self.data[line])
                out_file.write(line_str)

if __name__=="__main__":
    pass
