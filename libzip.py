# zip parser
# ported from https://github.com/ndesmic/zip/tree/v1.0
import sys, zlib
_BYTEORDER = sys.byteorder
FILE_ENTRY = '04034b50'
CDIR_ENTRY = '02014b50'
CDIR_END   = '06054b50'
#utility
def get(b, t, l=1):
    if (t=="uint8"): return int.from_bytes(b.read(l*1), _BYTEORDER)
    if (t=="uint16"): return int.from_bytes(b.read(l*2), _BYTEORDER)
    if (t=="uint32"): return int.from_bytes(b.read(l*4), _BYTEORDER)
    if (t=="string"):
        #prevent unicode errors by parsing ascii
        bstr = b.read(l)
        str = ""
        for i in range(0, len(bstr)): str += chr(bstr[i])
        return str
    if (t=="hex"): return hex(int.from_bytes(b.read(l), _BYTEORDER)).replace("x", "")[-l*2:]

#serve slices (files) of the archive file buffer as file io stream
from io import IOBase
class SubFileStream(IOBase):
    def __init__(self, buf, offset, length):
        self.b = buf
        self.o = offset
        self.l = length
        self.b.seek(self.o)
        #print("SUBFILE", offset, length)
   
    def read(self, sz=65536):
        if self.l == 0:
            return b""
        if sz > self.l:
            sz = self.l
        data = self.b.read(sz)
        sz = len(data)
        self.l -= sz
        return data
    
    def readinto(self, buf):
        if self.l == 0:
            return 0
        if len(buf) > self.l:
            buf = memoryview(buf)[:self.l]
        sz = self.b.readinto(buf)
        self.l -= sz
        return sz
    
    def close(self):
        pass
    
       
#main zip archive class                
class ZipFile:
    def __init__(self, buf, files):
        self.b = buf
        self.files = files
        self.sub = None
    
    def extract(self, i):
        self.sub = SubFileStream(self.b, i["startsAt"], i["compressedSize"])
        if i["compressionMethod"] == 0: #no compression
            #print("EXTRACT", i["fileName"], 0, i["compressedSize"], i["uncompressedSize"])
            return self.sub
        elif i["compressionMethod"] == 8: #raw deflate
            #print("EXTRACT", i["fileName"], 8, i["compressedSize"], i["uncompressedSize"])
            self.sub = SubFileStream(self.b, i["startsAt"], i["compressedSize"])
            return zlib.DecompIO(self.sub, -16)
    
       
    def close(self):
        self.sub = None
        self.b.close()

#zip parser
class Zip:
    def __init__(self):
        pass

    def open(self, file=None, fileobj=None):
        if fileobj:
            b = fileobj
        else:
            b = open(file, "rb")
        
        localFiles = []
        centralDirectories = []
        endOfCentralDirectory = None
        
        while not endOfCentralDirectory:
            e = { "signature": get(b, "hex", 4) } #uint32
            if e["signature"] == FILE_ENTRY:
                #print("[FILE ENTRY]")
                e["version"] = get(b, "uint16")
                e["generalPurpose"] = get(b, "uint16")
                e["compressionMethod"] = get(b, "uint16")
                e["lastModifiedTime"] = get(b, "uint16")
                e["lastModifiedDate"] = get(b, "uint16")
                e["crc"] = get(b, "hex", 4) #uint32
                e["compressedSize"] = get(b, "uint32")
                e["uncompressedSize"] = get(b, "uint32")
                e["fileNameLength"] =  get(b, "uint16")
                e["extraLength"] = get(b, "uint16") 
                e["fileName"] = get(b, "string", e["fileNameLength"])
                e["extra"] = get(b, "string", e["extraLength"])
                e["startsAt"] = b.tell()
                localFiles.append(e)
                #skip file content
                b.seek(e["startsAt"]+e["compressedSize"])
                #print (e)
            elif e["signature"] == CDIR_ENTRY:
                #print("[CDIR ENTRY]")
                e["versionCreated"] = get(b, "uint16")
                e["versionNeeded"] = get(b, "uint16")
                e["generalPurpose"] = get(b, "uint16")
                e["compressionMethod"] = get(b, "uint16")
                e["lastModifiedTime"] = get(b, "uint16")
                e["lastModifiedDate"] = get(b, "uint16")
                e["crc"] = get(b, "hex", 4) #uint32
                e["compressedSize"] = get(b, "uint32")
                e["uncompressedSize"] = get(b, "uint32")
                e["fileNameLength"] =  get(b, "uint16")
                e["extraLength"] = get(b, "uint16")
                e["fileCommentLength"] = get(b, "uint16")
                e["diskNumber"] = get(b, "uint16")
                e["internalAttributes"] = get(b, "uint16")
                e["externalAttributes"] = get(b, "uint32")
                e["offset"] = get(b, "uint32")
                e["fileName"] = get(b, "string", e["fileNameLength"])
                e["extra"] = get(b, "string", e["extraLength"])
                e["comments"] = get(b, "string", e["fileCommentLength"])
                centralDirectories.append(e) 
                #print (e)
            elif e["signature"] == CDIR_END:
                #print("[CDIR END]")
                e["numberOfDisks"] = get(b, "uint16")
                e["centralDirectoryStartDisk"] = get(b, "uint16")
                e["numberCentralDirectoryRecordsOnThisDisk"] = get(b, "uint16")
                e["numberCentralDirectoryRecords"] = get(b, "uint16")
                e["centralDirectorySize"] = get(b, "uint32")
                e["centralDirectoryOffset"] = get(b, "uint32")
                e["commentLength"] = get(b, "uint16")
                e["comment"] = get(b, "string", e["commentLength"])
                endOfCentralDirectory = e
                #print (e)
        
        return ZipFile(b, localFiles)



"""
zip = Zip()
z = zip.open("/download/mqtt_upython-master.zip")
for i in z.files:
    if i["fileName"][-1] == "/":
        print("DIR", i["fileName"])
        #mkdir(i["fileName"][:-1])
    else:
        print("FILE", i["fileName"])
        #cp(z.extract(i), open(i["fileName"], "wb+"), buffers=True)
z.close()
"""
