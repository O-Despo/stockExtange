from PyPDF2 import PdfReader
import re
import yfinance as yf

#Exceptions
class badPlatform(Exception):
    def __init__(self, platforms, platform, *args):
        #super.__init__(args)
        self.platforms = platforms
        self.platform  = platform


class RobinHood():
    def __init__(self):
        self.platforms = {
                "rh": self.rh,
                }
    
    def run(self, file_source, platform):
        if (platform in self.platforms.keys()) == False:
            raise badPlatform(self.platforms, platform)
        
        pdf = PdfReader(file_source)
        output = self.platforms[platform](pdf)
        
        #Create list of all stocks on invoice
        port_val_stocks = [i[0] for i in output["portInfo"]]
        acount_sum_stocks = [i[0] for i in output["transactionsInfo"]]
        all_stocks = set(port_val_stocks + acount_sum_stocks)
        all_stocks = dict(zip(all_stocks, [0, 0, 0]))
        
        breakpoint()
        for tract in output["transactionsInfo"]:
            if tract[1] == "Buy":
                all_stocks[tract[0]][0] -= float(tract[3])
                all_stocks[tract[0]][2] -= float(tract[2])
            else:
                all_stocks[tract[0]][1] += float(tract[3])
                all_stocks[tract[0]][2] += float(tract[2])

        print(all_stocks)
        return output

    def rh(self, pdf):
        patterns = {
                "portValue": re.compile("Portfolio Value\\n \$(.*?)\\n\$(.*?)\\n"),
                "dateRange": re.compile("com\\n\\n(.*?) to (.*?)\\n"),
                }

        output = {
                "portValue": None,
                "dateRange": None,
                "overallChange": None,
                "portInfo": None,
                "transactionsInfo": None,
                }
        # General info
        to_float = lambda i: float(i) if i.replace(".","").isdigit() else i

        page_text_0 = pdf.pages[0].extract_text()
        port_value_extract = re.search(patterns["portValue"], page_text_0)

        output["portValue"] = [to_float(i) for i in port_value_extract.group(1, 2)]
        output["overallChange"] = -(100 - output["portValue"][1]/(output["portValue"][0]/100))
        date_range_extract = re.search(patterns["dateRange"], page_text_0)
        output["dateRange"]  = date_range_extract.group(1, 2)

        # transactions
        acount_activity_ptrn = re.compile("Account Activity")
        portfolio_summary_ptrn = re.compile("Portfolio Summary")

        acount_activity = ""
        portfolio_summary = "" 

        for page in pdf.pages[:]:
            text = page.extract_text()
            if acount_activity_ptrn.search(text): acount_activity += text
            elif portfolio_summary_ptrn.search(text): portfolio_summary += text

        transaction_prtn = re.compile("CUSIP.*?\n (.*?)\n.*?\n(.*?)\n.*?\n(.*?)\n\$.*?\n\$(.*?)[\n, ]")
        transactions = transaction_prtn.findall(acount_activity)
        output["transactionsInfo"] = transactions

        portfolio_prtn = re.compile("E.*?%\n(.*?)\n.*?(\n.*?)\n.*?\n\$(.*?)[\n, ]")
        current_port_info = portfolio_prtn.findall(portfolio_summary)
        output["portInfo"] = current_port_info

        return output

if __name__ == "__main__":
    rh = RobinHood()
    out = rh.run("robinhood.pdf", "rh")
