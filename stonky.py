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
                "delete": self.delete,
                "deleteconfirm": self.deleteConfirm,
                "datadownload": self.dataDownload
                }       
        
        self.actions = {
                "leaderBoard": self.board,
                "stats": self.stats
        }

        #db
        self.start_db_connection()

    def start_db_connection(self):
        self.mongoClient = MongoClient(os.getenv("MONGO_URL"))
        self.db = self.mongoClient[os.getenv("DB")]
        self.user_col = self.db["users"]
        self.records_col = self.db["records"]

        self.log.debug(f"Connected to db {os.getenv('MONGO_URL')}")

    async def board(self):
        pass

    async def stats(self):
        pass

    async def dataDownload(self, parsed_content, msg):
        if len(parsed_content) > 1:
            response = self.user_col.find({"discord_id", msg.author.id})
            
            file_name = str(uuid.uuid1()) + json
            with open(file_name, "w+") as json_out:
                json.dump(response, json_out)

            discord_file = discord.file(file_name)
            msg.author.send(discord_file)

            os.rm(file_name)

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

            term_date = data["dates"][0][0:7]
            term_entry = {term_date: data}
            
            user_entry = self.user_col.find_one({"discord_id": msg.author.id})
            
            #check if term already enterned  
            if "o" in parsed_content: overwite = True
            else: overwite = False

            if user_entry and term_date in user_entry["terms"].keys() and overwite == False:
                msg.author.send(f"the term {term_date} has already been added add `:o` to overwrite the term")
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

            self.log.info(f"TERM made for {msg.author.id} date {term_date}")

            await msg.author.send(f"Sucess entry made for {term_date}")
            
    async def delete(self, parsed_content, msg):
        """create a deletion confoamtion code"""
        code = random.randint(1000,9999)
        tries = 0

        #Error hadnling
        in_db = self.user_col.find_one({"discord_id": msg.author.id})

        if not in_db:
            await msg.author.send("your data is not present there is nothing to delete")

        while(code in self.delete_tokens.keys()):
            code = random.randint(999,1000)

            tries += 1
            if tries >= 10:
                await msg.author.send("failed to generate code try again")
                return
            
        self.delete_tokens[str(code)] = {"timeout": time.time() + 120, "id":  msg.author.id}

        await msg.author.send(f"your deletion token is {code}\nto inriversable delete all your data type `#deleteconfirm:{code}")
        
        
    async def deleteConfirm(self, parsed_content, msg):
        """Removes all data of user"""
        #Error correction
        error_msg = ""
        if len(parsed_content) != 2:
            error_msg += "please add in the forms of `#deleteconfirm:CODE'\nif you need a code use '#delete'"
        elif parsed_content[1] not in self.delete_tokens.keys(): 
            print(parsed_content)
            print(self.delete_tokens)
            error_msg += "that is not a register delection token"
        
        elif self.delete_tokens[parsed_content[1]]["timeout"] < time.time():
            error_msg += "This token is older than 2 minutes and is invalid\n"
            del self.delete_tokens[parsed_content[1]]
            error_msg += "This token has been removed\n"

        elif self.delete_tokens[parsed_content[1]]["id"] != msg.author.id:
            error_msg += "This token registered under another user"

        if error_msg:
            await msg.author.send(error_msg)
            return

        delele_outcome = self.user_col.find_one_and_delete({"discord_id": msg.author.id})
        if delele_outcome == None:
            await msg.author.send("your information has already been removed from or was never on our servers")
        else:
            await msg.author.send("Removed awaiting conformation")

        #TODO removed from logs
        if self.user_col.find_one({"discord_id": msg.author.id}) == None: 
            await msg.author.send("Information removed : CONFERMED")

        else:
            await msg.author.send("failed contact dev")

    async def query(self, parsed_msg, msg):
        """returns a given query"""
        self.possible.querys = {
                }
        pass

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

