import extract
import time
import discord
import os
import json
import uuid
import random
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class stonky(discord.Client):
    def __init__(self):
        super().__init__()
        self.pdf_extract= extract.pdfExtract()
        self.platforms = self.pdf_extract.platforms.keys()
        self.delete_tokens = {}
        
        #set up logging 
        self.log = logging.getLogger(os.getenv("LOG_NAME"))
        self.log.setLevel(logging.DEBUG)

        self.file_log = logging.FileHandler(os.getenv("LOG_NAME") + ".log")

        self.stream_log = logging.StreamHandler() 

        formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(name)s : %(message)s")
        self.log.addHandler(self.file_log)
        self.log.addHandler(self.stream_log)
        self.file_log.setFormatter(formatter)
        self.stream_log.setFormatter(formatter)

        with open("msg_text.json", "r") as json_in:
            self.simple_msgs = json.load(json_in)

        self.dmActions = {
                "process": self.process,
                "query": self.query,
                "delete": self.deleteAll,
                "deleteconfirm": self.deleteConfirm,
                "datadownload": self.dataDownload
                }       
        
        self.actions = {
                "leaderBoard": self.getLeaderboard,
                "stats": self.stats
        }

        self.default_malform_criteria = {
                "number_of_args": None,
                "args_are_in": None,
                "attachments_required": None,
                "attachment_content_type": None,
                }

        self.delete_codes = {}

        #db
        self.getBoardCats = ["overall", "singleStock"]
        self.start_db_connection()

    def start_db_connection(self):
        self.mongoClient = MongoClient(os.getenv("MONGO_URL"))
        self.db = self.mongoClient[os.getenv("DB")]
        self.user_col = self.db["users"]
        self.records_col = self.db["records"]

        self.log.debug(f"Connected to db {os.getenv('MONGO_URL')}")

    async def getLeaderboard(self, msg_parts, msg):
        """gets the leaderboard for a given term"""
        get_leaderboard_malform_detect = self.default_malform_criteria.copy()
        get_leaderboard_malform_detect["number_of_args"] = 2
        get_leaderboard_malform_detect["args_are_in"] = [self.getBoardCats, None]
        
        malformed = self.malformDetection(get_leaderboard_malform_detect, msg)
        if malformed[0]:
            await msg.author.send("COMMAND_MALFORMED\n" + malformed[1])
            return 3

        args = malformed[2]
        
        self.updateLeaderboard(arg[1])
        db_response = sell.leader_col.find_one({
            "term": args[0]
            })

        await msg.author.send(db_response["stings"][args[1]])
        return 0


    async def updateLeaderboard(self, term):
        pass

    def malformDetection(self, criteria, msg):
        """detects malformation given a set of criteria"""
        malformed = False
        malformMessage = ""

        args = msg.clean_content.split(" ")[1:]

        if criteria["number_of_args"] != None:
            num_of_args = criteria["number_of_args"]
            
            if type(number_of_args) == list:
                #Only for development
                if len(number_of_args) != 2:
                    self.log.ERROR("incorect number of args suplied as criteria to malformDetection")
                    raise AssertionError("wrong number of argumnets in number_of_args criteria")
                
                #code that will hit user
                if len(args) < number_of_args[0]:
                    malformMessage += "Not enough arguments suplied: expected minimum of {number_of_args[0]}"
                elif len(args) < number_of_args[1]:
                    malformMessage += "To many arguments suplied: expected maximun of {number_of_args[0]}"
            else:
                if len(args) != number_of_args:
                    malformMessage += "Incorect amount of argumnets: expected {number_of_args}"

        #if criteria["type_of_args"] != None:
        #    type_of_args = criteria["type_of_args"]

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

        if malformMessage != "":
            return (False, malformMessage)
        else:
            return (True, "message not malformed")

    async def stats(self):
        pass

    async def dataDownload(self, parsed_content, msg):
        """downloads all the data stored on the Stonky server"""
        if len(parsed_content) == 1:
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

    async def process(self, parsed_content, msg):
        #Error check
        self.pro_error = False
        error_msg = ""

        if len(parsed_content) < 2:
            error_msg += f"provided platform after semicolon `process:PLATFORM`\nThe available plaltforms are {self.platforms}\n"
        elif parsed_content[1] not in self.platforms:
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
            data = self.pdf_extract.run(file_name, parsed_content[1])
            
            os.remove(file_name)
            
            term = data["term"]
            term_entry = {data["term"]: data}
            
            user_entry = self.user_col.find_one({"discord_id": msg.author.id})
            
            #check if term already enterned  
            if "o" in parsed_content: overwite = True
            else: overwite = False

            if user_entry and term in user_entry["terms"].keys() and overwite == False:
                await msg.author.send(f"the term {term} has already been added add `:o` to overwrite the term")
                return

            if user_entry == None:
                user_entry = {
                        "discord_id": msg.author.id,
                        "terms": term_entry
                        }
                self.user_col.insert_one(user_entry)

            else:
                user_entry["terms"].update(term_entry)
                self.user_col.update_one({"discord_id": msg.author.id}, {"$set":{"terms": user_entry["terms"]}})

            self.log.info(f"TERM made for {msg.author.id} date {term}")

            await msg.author.send(f"Sucess entry made for {term}")
            
    async def deleteAll(self, parsed_content, msg):
        """create a deletion confoamtion code"""
        self.checkDeleteCodeTimeouts()

        #Error handling
        errorMsg = ""
        #user_has_code = self.userHasDeleteCode(msg) 
        #TODO remove delete code timrout
        #if user_has_code[0] == False: errorMsg += user_has_code[1]
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
        """cleans the delete codes stack"""
        for delete_code_item in self.delete_codes.items():
            if delete_code_item[1]["timeout"] < time.time():
                del self.delete_codes[delete_code_item[0]]
                self.log.debug("{msg.author.id} delete code {delete_code_item[1]['code'] removed due to timeout")

    def validDeleteCode(self, code, msg):
        """verifys deletiond code returns (verifies_status:bool, msg)"""
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
        """checks if a user already has a deletion code"""
        hasCode = False
        returnMsg = ""

        if msg.author.id in self.delete_codes.keys(): 
            hasCode = True
            returnMsg += f"{msg.author.name} already has a deletion code {self.delete_codes[msg.author.id]}\n"
        
        return (hasCode, returnMsg)
        
    async def deleteConfirm(self, parsed_content, msg):
        """Removes all data of user after taking in verified deletion code"""
        #Error correction
        self.checkDeleteCodeTimeouts()
        error_msg = ""
       
        if len(parsed_content) != 2:
            error_msg += "please ensure the command takes the form deleteConfirm:code"
            await msg.author.send(error_msg)
            return 0
        
        code = parsed_content[1]
        valid_code = self.validDeleteCode(code, msg)
        if valid_code[0] == False:
            error_msg += valid_code[1]
            await msg.author.send(error_msg)
            return 0

        delele_outcome = self.user_col.find_one_and_delete({"discord_id": msg.author.id})
        if delele_outcome == None:
            await msg.author.send("your information has already been removed from or was never on our servers")
        self.log.debug(f"{msg.author.id} deleted all data useing code {parsed_content[1]})")

        if self.user_col.find_one({"discord_id": msg.author.id}) == None: 
            await msg.author.send("Information removed : CONFIRMED")
        else:
            await msg.author.send("failed contact dev")

    async def query(self, parsed_msg, msg):
        """returns a given query"""
        self.possible.querys = {
                }

    async def dmProcessMsg(self, parsed_content, msg):
        if parsed_content[0] in self.dmActions.keys():
            func = self.dmActions[parsed_content[0]]
            await func(parsed_content, msg)
        else:
            await msg.author.send(self.simple_msgs["help"])

    async def serverProcessMsg(self, parsed_content, msg):
        if parsed_content[0] in self.simple_msgs.keys():
            output = self.simple_msgs[parsed_content[0]]
            msg.author.send(output)

    async def inDm(self, parsed_content, msg):
        if type(msg.channel) == discord.DMChannel:
            await msg.author.send("This is a DM channel")
        else:
            await msg.author.send("This is NOT a DM channel")

    async def on_message(self, msg):
        common = {
                "indm": self.inDm}
        text_content = msg.clean_content.lower()
        
        if text_content[0] != os.getenv("MSG_ID"): return
        self.log.debug(f"Message recieved:{text_content}")

        #clean text input
        text_content = text_content[1:]
        text_content = text_content.replace(" ", "")
        content_parse = text_content.split(":")

        #TODO remain charater 
        if content_parse[0] in self.simple_msgs:
            await msg.author.send(self.simple_msgs[content_parse[0]])

        elif content_parse[0] in common.keys():
            await common[content_parse[0]](content_parse, msg)

        else:
            if type(msg.channel) == discord.DMChannel:
                await self.dmProcessMsg(content_parse, msg) 
            else:
                await self.serverProcessMsg(content_parse, msg)
 
    async def on_connect(self):
        self.log.debug("Connected to discord")
   
if __name__ == "__main__":
    stonkBot = stonky()
    stonkBot.run(os.getenv("DISCORD_KEY"))

