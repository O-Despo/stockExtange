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
                    "transactedAmount": round(transacted_amount, 5), 
                    "debit": round(debit, 2), 
                    "credit": round(credit, 2),
                    }
        
        starting_amount = {}
        breakpoint()
        for ticker in all_stocks.keys():
            if port.get(ticker):
                starting_amount[ticker] = port[ticker]["amount"] - all_stocks[ticker]["transactedAmount"]
            else:
                starting_amount[ticker] = -all_stocks[ticker]["transactedAmount"]
        tickers_to_pull = ""

        for ticker in starting_amount.keys():
            tickers_to_pull += ticker + " "

        #Format date to %Y-%M-%D
        date = output["dateRange"][0]
        date = f"{date[6:]}-{date[0:2]}-{date[3:5]}"
        date_end = f"{date[0:8]}{int(date[8:10]) + 1}"

        ticker_data = yf.download(tickers=tickers_to_pull, start=date, end=date_end, interval="1d")
       
        for stock in starting_amount.items():
            all_stocks[stock[0]]["debit"] += round(ticker_data.at[date, ("Close", stock[0])] * stock[1], 2)
            if port.get(stock[0]):
                all_stocks[stock[0]]["credit"] += port[stock[0]]["value"]
        
        for stock in all_stocks.items():
            print(stock[0], stock[1]["debit"])
        breakpoint()
        for stock in all_stocks.items():
            all_stocks[stock[0]]["yield"] = round((stock[1]["credit"] - stock[1]["debit"])/stock[1]["debit"] * 100, 4)

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
