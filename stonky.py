import extract
import time
import discord
import os
import json
import uuid
import random
import logging
import re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class stonky(discord.Client):
    """Sub class of discord.Client contains all logic for discord bot."""
    def __init__(self):
        super().__init__()
        self.pdf_extract= extract.pdfExtract()
        self.platforms = self.pdf_extract.platforms.keys()
        self.delete_tokens = {}
 
        self.COMMANDS = {
                "process": self.process,
                "query": self.query,
                "delete": self.deleteAll,
                "deleteconfirm": self.deleteConfirm,
                "datadownload": self.dataDownload,
                "leaderboard": self.getLeaderboard,
                "stats": self.stats,
                }       
        
        self.default_malform_criteria = {
                "number_of_args": None,
                "args_are_in": None,
                "attachments_required": None,
                "attachment_content_type": None,
                "meets_regex": None
                }

        #Regex pttrns for malform detection
        self.legit_term_ptrn = re.compile("\d{4}-\d{2}")

        #start logging
        self.start_logging()

        #Connect to db
        self.start_db_connection()

    def start_logging(self):
        """sets up logging"""
        self.log = logging.getLogger(os.getenv("LOG_NAME"))
        self.log.setLevel(logging.DEBUG)

        self.file_log = logging.FileHandler(os.getenv("LOG_NAME") + ".log")

        self.stream_log = logging.StreamHandler() 

        formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(name)s : %(message)s")
        self.log.addHandler(self.file_log)
        self.log.addHandler(self.stream_log)
        self.file_log.setFormatter(formatter)
        self.stream_log.setFormatter(formatter)

    def start_db_connection(self):
        """Starts the database connection."""
        self.mongoClient = MongoClient(os.getenv("MONGO_URL"))
        self.db = self.mongoClient[os.getenv("DB")]
        self.user_col = self.db["users"]
        self.records_col = self.db["records"]

        self.log.debug(f"Connected to db {os.getenv('MONGO_URL')}")

    async def on_message(self, msg):
        """Given that the message has a vaild command runs command otherwise runs help

        :param msg: the msg recieved by the bot
        :type msg: discord.Message
        """
        text_content = msg.clean_content.lower()
        
        if text_content[0] != os.getenv("MSG_ID"): return
        self.log.debug(f"Message recieved:{text_content}")

        #Clean text input
        text_content = text_content[1:]
        text_content = text_content.replace(" ", "")
        args = text_content.split(":")

        if args[0] in self.COMMANDS.keys():
            await self.COMMANDS[args[0]](args, msg)
        else:
            await msg.author.send("HELP") 

    async def getLeaderboard(self, args, msg):
        """Get the user request for leader baord
        
        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message

        :rtype: int
        :return: 1 if falied 0 is sucess
        """
        get_leaderboard_malform_detect = self.default_malform_criteria.copy()
        get_leaderboard_malform_detect["number_of_args"] = 2
        get_leaderboard_malform_detect["meets_regex"] = [None, self.legit_term_ptrn]
        
        malformed = self.malformDetection(get_leaderboard_malform_detect, args, msg)
        if malformed[0]:
            await msg.author.send("COMMAND_MALFORMED\n" + malformed[1])
            return 1

        db_response = self.updateLeaderboard(args[1])
        return 0

    def updateAllLeaderboards(self):
        """Updates every term leaderboard in the database."""
        pass

    def buildLeaderboard(self, term):
        """Build the leaderbaords from scractch given a term
 
        :param term: the time term to update (year-month) ex. (2022.03)
        :type term:str           

        :rtype: dict
        :return: the build leader baord
        """
        pass

    def updateLeaderboard(self, term):
        """Updates a leaderboard with the given term.

        :param term: the time term to update (year-month) ex. (2022.03)
        :type term:str
        """
        lb_term_prj = {f"terms.{term}": True, "discord_name": True}
        lb_term_sort = [(f"terms.{term}.overallChange", -1)]
        lb_term_filter = {f"terms.{term}":  {"$exists": True}}
        
        pure_response = self.user_col.find(filter=lb_term_filter, projection=lb_term_prj, sort=lb_term_sort)
        pure_response["terms"]

        for response_item in pure_response:
            pass

        overall_change = None
                 
    def malformDetection(self, criteria, args, msg):
        """Detect malformation given a set of criteria returns a malformMsg and reason for malform.
        
        :param criteria: the criteria that the msg should conform to
        :type criteria: dict

        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message

        :rtype: (bool, str)
        :return: (malformed, messasage response), weither malformed, the response msg
        """
        malformMessage = ""

        if criteria["number_of_args"] != None:
            number_of_args = criteria["number_of_args"]
            if type(number_of_args) == list:
                #Only for development
                if len(number_of_args) != 2:
                    self.log.ERROR("incorect number of args suplied as criteria to malformDetection")
                    raise AssertionError("wrong number of argumnets in number_of_args criteria")
                
                #code that will hit user
                if len(args) < number_of_args[0]:
                    malformMessage += f"Not enough arguments suplied: expected minimum of {number_of_args[0]}"
                elif len(args) < number_of_args[1]:
                    malformMessage += f"To many arguments suplied: expected maximun of {number_of_args[0]}"
            else:
                if len(args) != number_of_args:
                    malformMessage += f"Incorect amount of argumnets: expected {number_of_args}"

        if criteria["args_are_in"] != None:
            for i, arg in enumerate(args):
                if criteria["args_are_in"][i] != None:
                    possible_args_list =  criteria["args_are_in"][i]
                    if arg not in possible_args_list:
                        #format possible args
                        possible_args_list_str = ""
                        for possible_arg in possible_args_list:
                            possible_args_list_str += ", " + possible_arg

                        malformMessage += f"\"{arg}\" must be one of the following:{possible_args_list_str}\n"

        if criteria['attachments_required'] != None:
            if len(msg.attachments) == 0:
                    malformMessage += "A attachment is required"

        if criteria["attachment_content_type"] != None:
            for attachment in msg.attachments:
                if attachment.content_type != criteria["attachment_content_type"]:
                    malformMessage += f"{attachment.file_name} has the wrong type expected {criteria_content_type} fot {attachment.content_type}"

        if criteria["meets_regex"] != None and malformMessage == "":
            #TODO regex list should take format of [{pattern: pattern, format: format] TODO malform should have reason
            regex_list = criteria["meets_regex"]
            if type(regex_list) != list:
                self.log.ERROR("meets_regex must be suplied to criteria as list")
                raise TypeError("please supply a list to meets regex")
            
            for i, pttrn in enumerate(regex_list):
                if pttrn == None:
                    continue

                arg = args[i]
                pttrn_out_put = pttrn.findall(arg)
                
                if len(pttrn_out_put) != 1:
                    malformMessage += {f"{arg} is malformed"}
                    
        if malformMessage != "":
            return (True, malformMessage)
        else:
            return (False, "message not malformed")

    async def stats(self, args, msg):
        """Returns stats in a given term
        
        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
 
        pass

    async def dataDownload(self, args, msg):
        """Downloads all the data stored on the Stonky server returns it to user.
        
        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        if len(args) == 1:
            response = self.user_col.find_one({"discord_id": msg.author.id})

            if response == None:
                await msg.author.send("You have no data stored")
                return
            #_id must be removed so as json cannot serialize _id type
            del response["_id"]
            
            file_name = str(uuid.uuid1()) + ".json"
            with open(file_name, "w+") as json_out:
                json.dump(response, json_out)

            discord_file = discord.File(file_name)
            await msg.author.send(file=discord_file)
            await msg.author.send("data")
            os.remove(file_name)

    async def process(self, args, msg):
        """Processes the inputed file returns weither it was a sucess.
        
        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        self.pro_error = False
        error_msg = ""

        if len(args) < 2:
            error_msg += f"provided platform after semicolon `process:PLATFORM`\nThe available plaltforms are {self.platforms}\n"
        elif args[1] not in self.platforms:
            error_msg += f"The platform provided is not available\nThe available plaltforms are {self.platforms}\n"

        #Error handleing
        if msg.attachments == []:
            error_msg += f"Please add a attachment\n"

        else:
            if msg.attachments[0].content_type != "application/pdf":
                error_msg += f"please ensure your file is pdf\n"

            if len(msg.attachments) > 1:
                error_msg += f"Please only add one attachment\n"
        
        if error_msg:
            await msg.author.send("Failed\n" + error_msg)
            return
        
        #Process file
        else:
            file_name = "temp/" + str(uuid.uuid1()) + ".pdf" 
            await msg.attachments[0].save(file_name)
            data = self.pdf_extract.run(file_name, args[1])
            
            os.remove(file_name)
            
            term = data["term"]
            term_entry = {data["term"]: data}
            
            user_entry = self.user_col.find_one({"discord_id": msg.author.id})
            
            #check if term already enterned  
            if "o" in args: overwite = True
            else: overwite = False

            if user_entry and term in user_entry["terms"].keys() and overwite == False:
                await msg.author.send(f"the term {term} has already been added add `:o` to overwrite the term")
                return

            #Sort summary based on overall yeild
            yeild_index_dict = {info["yield"]:stock for (stock, info) in data["summary"].items()}
            yeild_list = list(yeild_index_dict.keys())
            yeild_list.sort()
            yeild_list.reverse()
            
            new_summary = {}
            for yeild in yeild_list:
                new_summary[yeild_index_dict[yeild]] = data["summary"][yeild_index_dict[yeild]]
            
            data["summary"] = new_summary
                
            if user_entry == None:
                user_entry = {
                        "discord_id": msg.author.id,
                        "discord_name": msg.author.name,
                        "terms": term_entry
                        }
                self.user_col.insert_one(user_entry)

            else:
                user_entry["terms"].update(term_entry)
                self.user_col.update_one({"discord_id": msg.author.id}, {"$set":{"terms": user_entry["terms"]}})

            self.log.info(f"TERM made for {msg.author.id} date {term}")

            await msg.author.send(f"Sucess entry made for {term}")
    
    async def deleteAll(self, args, msg):
        """Generate a code to delele all user data
        
        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        self.checkDeleteCodeTimeouts()

        #Error handling
        errorMsg = ""
        if self.user_col.find_one({"discord_id": msg.author.id}) == None: errorMsg += "Nothing to delete\n"
         
        if errorMsg != "":
            await msg.author.send(errorMsg)
            return 0

        #Generation Logic
        code = random.randint(1000,9999)
        self.delete_codes[msg.author.id] = {"timeout": time.time() + 1, "code":  code}

        await msg.author.send(f"your deletion token is {code}\nto inriversablely delete all your data type `#deleteconfirm:{code}")
        self.log.debug(f"{msg.autho.id} created a delete code {code}")
        return 1

    def checkDeleteCodeTimeouts(self):
        """Cleans the delete codes stack"""
        for delete_code_item in self.delete_codes.items():
            if delete_code_item[1]["timeout"] < time.time():
                del self.delete_codes[delete_code_item[0]]
                self.log.debug("{msg.author.id} delete code {delete_code_item[1]['code'] removed due to timeout")

    def validDeleteCode(self, code, msg):
        """verifys deletion code ruturn if vaild.
        
        :param code: the code the user suplied
        :type code: int

        :param msg: the full msg class
        :type msg: discord.Message

        :rtype: (bool, str)
        :return: (valid, returnMsg), wether the code is vaild, the msg to be used in response
        """
        vaild = True
        returnMsg = ""

        hasCode = self.userHasDeleteCode(msg)
        if hasCode[0]:
            if (self.delete_codes[msg.author.id]["code"] == code) == False:
                vaild = False
                returnMsg += "that dose not match your current deletion code"
        else:
            valid = False
            returnMsg += hasCode[1]
        return (vaild, returnMsg)
            
    def userHasDeleteCode(self, msg):
        """Checks if a user already has a deletion code
        
        :param msg: the full msg object
        :type msg: discord.Message

        :rtype: (bool, msg)
        :return: (hasCode, returnMsg), wether the user has a code, the msg to be used in response
        """
        hasCode = False
        returnMsg = ""

        if msg.author.id in self.delete_codes.keys(): 
            hasCode = True
            returnMsg += f"{msg.author.name} already has a deletion code {self.delete_codes[msg.author.id]}\n"
        
        return (hasCode, returnMsg)
        
    async def deleteConfirm(self, args, msg):
        """Takes in valid delete code and removes all data

        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        #Error correction
        self.checkDeleteCodeTimeouts()
        error_msg = ""
       
        if len(args) != 2:
            error_msg += "please ensure the command takes the form deleteConfirm:code"
            await msg.author.send(error_msg)
            return 0
        
        code = args[1]
        valid_code = self.validDeleteCode(code, msg)
        if valid_code[0] == False:
            error_msg += valid_code[1]
            await msg.author.send(error_msg)
            return 0

        delele_outcome = self.user_col.find_one_and_delete({"discord_id": msg.author.id})
        if delele_outcome == None:
            await msg.author.send("your information has already been removed from or was never on our servers")
        self.log.debug(f"{msg.author.id} deleted all data useing code {args[1]})")

        if self.user_col.find_one({"discord_id": msg.author.id}) == None: 
            await msg.author.send("Information removed : CONFIRMED")
        else:
            await msg.author.send("failed contact dev")

    async def query(self, args, msg):
        """Given a query retursn pure data

        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        pass 

    async def inDm(self, args, msg):
        """Given a query retursn pure data

        :param args: the args passed to the program
        :type args: list

        :param msg: the full msg object
        :type msg: discord.Message
        """
        if type(msg.channel) == discord.DMChannel:
            await msg.author.send("This is a DM channel")
        else:
            await msg.author.send("This is NOT a DM channel")
    async def on_connect(self):
        self.log.debug("Connected to discord")
   
if __name__ == "__main__":
    stonkBot = stonky()
    stonkBot.run(os.getenv("DISCORD_KEY"))
"""Processes the inputed file returns weither it was a sucess.

:param args: the args passed to the program
:type args: list

:param msg: the full msg object
:type msg: discord.Message
"""
