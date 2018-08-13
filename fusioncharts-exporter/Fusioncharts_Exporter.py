from django.shortcuts import render
from django.http import HttpResponse
from django.http import QueryDict
from PIL import Image

import codecs, string, random, hashlib, cairosvg, json, os

def getobject(request):

    
    exportMgr = ExportManager(request)
    response = exportMgr.Export()

    if response != None :
        return  response
    
    return HttpResponse(status=204)


class ExportManager:
    # Path where all images/pdf/svg will be stored in server side.
    # Path will be created within project directory
    __FUSIONCHARTS_EXP_DIR = "fusioncharts/Exported_Files/"

    # Define supported mime types
    __mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'png': 'image/png',
        'pdf': 'application/pdf',
        'svg': 'image/svg+xml'
    }

    __formData = None
    __options = None

    # Class constructor takes only http request as parameter
    def __init__(self, request):
        self.__formData = QueryDict(request.body)
        self.__options = QueryDict(self.__formData["parameters"].replace('|','&'))

    def __downloadable(self):
        if self.__options["exportaction"].lower() == "download":
            return True
        else:
            return False

    def __saveable(self):
        if self.__options["exportaction"].lower() == "save":
            return True
        else:
            return False
    
    def __exportFormat(self):
        return self.__options["exportformat"].lower()

    def __exportFilename(self):
        return self.__options["exportfilename"]

    def Export(self):

        func_switcher = {
            'jpg': self.__convertPNGToJPG,
            'jpeg': self.__convertPNGToJPG,
            'png': cairosvg.svg2png,
            'pdf': cairosvg.svg2pdf,
            'svg': cairosvg.svg2svg
        }
        func = func_switcher.get(self.__exportFormat())
        file_path = self.__getExportFilePath(self.__exportFormat())
        response = None

        if self.__downloadable():
            func(bytestring=self.__formData['stream'], write_to=file_path)
            response = self.__buildResponse(file_path, self.__exportFilename() + "." + self.__exportFormat())
        elif self.__saveable():
            func(bytestring=self.__formData['stream'], write_to=file_path)
        
        return response

    def __generateUniqueFileName(self, fileExtension):
        randStr = self.__getRandomString()
        hashlibObj = hashlib.md5()
        hashlibObj.update(randStr.encode('utf-8'))
        return hashlibObj.hexdigest() + "." + fileExtension
        
    def __getRandomString(self, size=10, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def __getExportLocation(self):
        settings_dir = os.path.dirname(__file__)
        projectRootPath = os.path.abspath(os.path.dirname(settings_dir))
        export_directory = os.path.join(projectRootPath, self.__FUSIONCHARTS_EXP_DIR)
        self.__createDirectory(export_directory)
        return export_directory

    def __getExportFilePath(self, fileExtension):
        return os.path.join(self.__getExportLocation(), self.__generateUniqueFileName(fileExtension))

    def __writeContentInDiskFile(self, filePath, content):
        file = codecs.open(filePath, "w", "utf-8")
        file.write(u'\ufeff')
        file.write(content)
        file.close()

    def __buildResponse(self, filePath, fileName = None):
        response = None
        if os.path.exists(filePath):
            with open(filePath, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type= self.__mime_types[self.__exportFormat()])
                response["Access-Control-Allow-Headers"] = "*"
                response["Access-Control-Allow-Methods"] = "GET, POST"
                response["Access-Control-Allow-Origin"] = "*"
                response['Content-Disposition'] = 'attachment; filename=' + (os.path.basename(filePath) if fileName == None else fileName)
                response['Content-Length'] = os.path.getsize(filePath)
        
        self.__removeFile(filePath)
        return response

    def __removeFile(self, filePath):
        if os.path.exists(filePath):
            os.remove(filePath)

    def __createDirectory(self, dirPath):
        directory = os.path.dirname(dirPath)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def __convertPNGToJPG(self, bytestring, write_to):
        cairosvg.svg2png(bytestring=bytestring, write_to=write_to)
        im = Image.open(write_to)
        rgb_im = im.convert('RGB')
        rgb_im.save(write_to)