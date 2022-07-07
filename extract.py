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

        #Transform port and transactions into dict
        transactions = {transaction[0]: [] for transaction in output["transactionsInfo"]}
        for transaction in output["transactionsInfo"]:
            transactions[transaction[0]].append({
                    "type": transaction[1],
                    "amount": float(transaction[2]),
                    "value": float(transaction[3]),
                    })
        
        port = {}
        for stock in output["portInfo"]:
            port[stock[0]] = {
                    "amount": float(stock[1]),
                    "value": float(stock[2]),
                    }
        
        all_stocks = dict.fromkeys(list(port.keys()) + list(transactions.keys()))

        for ticker in transactions.keys():
            debit = 0
            credit = 0 
            transacted_amount = 0
            for transaction in transactions[ticker]:
                if transaction['type'] == "Buy":
                    debit += transaction["value"]
                    transacted_amount += transaction["amount"]
                else:
                    credit += transaction["value"]
                    transacted_amount -= transaction["amount"]
            
            all_stocks[ticker] = {
                    "transactedAmount": transacted_amount, 
                    "debit": debit, 
                    "credit": credit,
                    }
        
        starting_amount = {}
        for ticker in port.keys():
            starting_amount[ticker] = port[ticker]["amount"] - all_stocks[ticker]["transactedAmount"]
        tickers_to_pull = ""
        for ticker in starting_amount.keys():
            tickers_to_pull += ticker + " "
        # Pull down ticker data
        # Add orinal dbit to caluation
        # Calcuate overall returns

                
        breakpoint()
        amount_held_start = {}
        

                    

       # for ticker in all_stocks.keys():

        portInfo = {}
        breakpoint()
        for stock in output["portInfo"]:
            portInfo[stock[0]] = {
                        "amount": stock[1],
                        "value": stock[2]
                        }

        for stock in all_stocks.items():
            if stock[0] in portInfo.keys():
                stock[1][3] = float(portInfo[stock[0]]["amount"]) - stock[1][2]
            else:
                stock[1][3] = - stock[1][2]
        
        for stock in all_stocks.items():
            ticker = yf.download(stock[0])
            
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

        portfolio_prtn = re.compile("E.*?%\n(.*?)\n.*?\n(.*?)\n.*?\n\$(.*?)[\n, ]")
        current_port_info = portfolio_prtn.findall(portfolio_summary)
        output["portInfo"] = current_port_info

        return output

if __name__ == "__main__":
    rh = RobinHood()
    out = rh.run("robinhood.pdf", "rh")
