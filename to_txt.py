from PyPDF2 import PdfReader

FILE_PATH = "robinhood.pdf"
OUT_PATH = "example_extract.txt"

pdf = PdfReader(FILE_PATH)
out_file = open(OUT_PATH, "w")

for page in pdf.pages:
    out_file.write(page.extract_text())
    out_file.write("\n!!!!!!PAGE BREAK!!!!!!!!!!!!!!!\n")

out_file.close()


