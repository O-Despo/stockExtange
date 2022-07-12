from PyPDF2 import PdfReader
import re
import yfinance as yf

#Exceptions
class badPlatform(Exception):
    def __init__(self, platforms, platform, *args):
        self.platforms = platforms
        self.platform  = platform

class pdfExtract():
    def __init__(self):
        self.platforms = {
                "rh": self.rh,
                }
    
    def run(self, file_source, platform):
        #Check if platform is correct
        if (platform in self.platforms.keys()) == False:
            raise badPlatform(self.platforms, platform)
        
        #Extract on pdf
        pdf = PdfReader(file_source)
        output = self.platforms[platform](pdf)

        print("PDF opened")

        #Transform port and transactions into dict
        port = output["portInfo"]
        transactions = output["transactionHistory"]
        all_stocks = dict.fromkeys(list(port.keys()) + list(transactions.keys()))
        
        #Compute the debit and credit from each tranaction
        stock_to_pull = ""
        for ticker in transactions.keys():
            debit = 0
            credit = 0 
            absoluteVolumeTransacted = 0

            for transaction in transactions[ticker]:
                if transaction['type'] == "Buy":
                    debit += transaction["value"]
                    absoluteVolumeTransacted += transaction["amount"]
                else:
                    credit += transaction["value"]
                    absoluteVolumeTransacted -= transaction["amount"]
            
            if port.get(ticker):
                volume_at_term_start = port[ticker]["amount"] - absoluteVolumeTransacted
            else:
                volume_at_term_start = - absoluteVolumeTransacted

            all_stocks[ticker] = {
                    "absoluteVolumeTransacted": round(absoluteVolumeTransacted, 5), 
                    "debit": debit, 
                    "credit": credit,
                    "volumeAtTermStart": volume_at_term_start,
                    }

            if volume_at_term_start != 0:
               stock_to_pull += ticker + " " 

        #Downloads history
        ticker_data = yf.download(tickers=stock_to_pull, start=self.start_date, end=self.end_date, interval="1d")
        ticker_data = ticker_data.to_dict()

        #Calulate yeild
        for stock in all_stocks.items():
            close = ticker_data.get(("Close", stock[0]))
            if close != None:
                close = list(close.values())[0]
                all_stocks[stock[0]]["debit"] += close * stock[1]["volumeAtTermStart"]

            if port.get(stock[0]):
                all_stocks[stock[0]]["credit"] += port[stock[0]]["value"]

            stock[1]["yield"] = (stock[1]["credit"] - stock[1]["debit"])/stock[1]["debit"] * 100

            for stock_values in stock[1].items():
                stock[1][stock_values[0]] = round(stock_values[1], 2)

        output["summary"] = all_stocks
        return output

    def rh(self, pdf):
        patterns = {
                "portValue": re.compile("Portfolio Value\\n \$(.*?)\\n\$(.*?)\\n"),
                "dateRange": re.compile("com\\n\\n(.*?) to (.*?)\\n"),
                "transactions": re.compile("CUSIP.*?\n (.*?)\n.*?\n(.*?)\n.*?\n(.*?)\n\$.*?\n\$(.*?)[\n, ]"),
                "portfolio": re.compile("E.*?%\n(.*?)\n.*?\n(.*?)\n.*?\n\$(.*?)[\n, ]"),
                }

        output = {
                "portValue": None,
                "dateRange": None,
                "term": None,
                "overallChange": None,
                "portInfo": None,
                "transactionHistory": None,
                }

        #Process text
        text = ""
        for page in pdf.pages[0:-1]:
            text += page.extract_text()


        to_float = lambda i: float(i) if i.replace(".","").isdigit() else i

        port_value_extract = re.search(patterns["portValue"], text)

        #Process basic stats
        output["portValue"] = [to_float(i) for i in port_value_extract.group(1, 2)]
        output["overallChange"] = -(100 - output["portValue"][1]/(output["portValue"][0]/100))

        date_range_extract = re.search(patterns["dateRange"], text)
        output["dateRange"] = date_range_extract.group(1, 2)


        #Format date to %Y-%M-%D
        date = date_range_extract.group(1, 2)[0]
        output["term"] = f"{date[6:]}-{date[0:2]}"

        self.start_date = f"{date[6:]}-{date[0:2]}-{date[3:5]}"
        self.end_date = f"{self.start_date[0:8]}{int(self.start_date[8:10]) + 1}"

        #Transactions
        transactions = patterns["transactions"].findall(text)
        output["transactionHistory"] = transactions

        transactions = {transaction[0]: [] for transaction in output["transactionHistory"]}
        for transaction in output["transactionHistory"]:
            transactions[transaction[0]].append({
                    "type": transaction[1],
                    "amount": float(transaction[2]),
                    "value": float(transaction[3]),
                    })
       
        #Port Info
        current_port_info = patterns["portfolio"].findall(text)
        output["portInfo"] = current_port_info

        port = {}
        for stock in output["portInfo"]:
            port[stock[0]] = {
                    "amount": float(stock[1]),
                    "value": float(stock[2]),
                    }
 
        output["portInfo"] = port
        output["transactionHistory"] = transactions
        return output

if __name__ == "__main__":
    import json
    rh = pdfExtract()
    out = rh.run("robinhood.pdf", "rh")
    print(json.dumps(out, sort_keys=True, indent=4))
