from PyPDF2 import PdfReader
import re
import yfinance as yf

input_file = PdfReader("testdoc.pdf")
print(input_file.getPage(0).extract_text())
print(input_file.metadata)

#Exceptions
class badPlatform(Exception):
    def __init__(self, platforms, platform, *args):
        #super.__init__(args)
        self.platforms = platforms
        self.platform  = platform

    def __str__(self):
        return f"{self.platform} is not a available platform,\nAvailable Platforms {self.platforms.keys()}"

class RobinHood():
    def __init__(self):
        self.platforms = {
                "rh": "placehodler"
                }
    
    def run(self, file_source, platform):
        if (platform in self.platforms.keys()) == False:
            raise badPlatform(self.platforms, platform)
        
        pdf = PdfReader(file_source)
        output = self.rh(pdf)
        return output

    def rh(self, pdf):
        patterns = {
                "portValue": re.compile("Portfolio Value\\n \$(.*?)\\n\$(.*?)\\n"),
                "dateRange": re.compile("com\\n\\n(.*?) to (.*?)\\n"),
                }

        output = {
                "portValue": None,
                "dateRange": None
                }
        page_text_0 = pdf.pages[0].extract_text()
        port_value_extract = re.search(patterns["portValue"], page_text_0)
        output["portValue"] = port_value_extract.group(1, 2)
        date_range_extract = re.search(patterns["dateRange"], page_text_0)
        output["dateRange"]  = date_range_extract.group(1, 2)

        return output

if __name__ == "__main__":
    rh = RobinHood()
    out = rh.run("testdoc.pdf", "rh")
    print(out)
