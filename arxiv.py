import arxiv
import openai
import glob
import re
import os
import csv
import shutil

# Setting up the directory for processing papers
dirpath = "<<PUT HERE THE FOLDER YOU WANT TO EXTRACT THE PAPERS TO>> " #Ex : "C:\\Users\\p"...
paperlistfile = "<<PUT HERE THE NAME OF CSV FILE THAT WILL CONTAIN THE LIST OF PAPERS AND THE SUMMARY>>" #"papers.csv"

# Setting up parameters for Azure OpenAI
openai.api_key = "<<API_KEY>>"
openai.api_base =  "https://<<YOUR RESOURCE NAME>>.openai.azure.com" # your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
openai.api_type = 'azure'
openai.api_version = '2022-12-01' # this may change in the future
deployment_name='<<NAME OF DEPLOYMENT>>' #This will correspond to the custom name you chose for your deployment when you deployed a model.

# Setting up search parameters for arxiv :
search = arxiv.Search(query = '<<PUT HERE THE KEYWORDS YOU WANT TO SEARCH>>', max_results = 25, sort_by = arxiv.SortCriterion.SubmittedDate)

# We reverse the list so that we start with the "oldest" papers
results = list(search.get())
results.reverse()

# Function to give a clean filename to the paper
def get_filename(self, extension: str = "pdf") -> str:
    nonempty_title = self.title if self.title else "UNTITLED"
    # Remove disallowed characters.
    clean_title = '_'.join(re.findall(r'\w+', nonempty_title))
    return "{}.{}.{}".format(self.get_short_id(), clean_title, extension)

# Getting existing files (we don't need to re-process these papers)
existing_papers = [os.path.basename(f) for f in glob.glob(dirpath+"*.pdf")]

for paper in results:
    filename = paper._get_default_filename()

    # If the paper has already been downloaded, we skip it
    if(filename in existing_papers):
        print('Paper '+filename+' already processed, skipping')
    else:
        print('Downloading paper '+filename)
        paper.download_pdf(dirpath=dirpath, filename=filename)

        # Processing the summary of the abstract
        print('Producing quick summary for paper '+filename)
        abstract=paper.summary.replace("'"," ")
        start_phrase = 'The text below is an abstract from a research paper, where the researchers present their work. Write a very short summary, one or two sentences max, of this abstract so that I can understand the content of the paper and share on professional social networks. \n\n'+abstract
        response = openai.Completion.create(engine=deployment_name, prompt=start_phrase, max_tokens=200)
        shortsummary = response['choices'][0]['text'].replace('\n', '').replace(' .', '.').strip()

        # Getting the line to add to the CSV file containing the list of papers
        row = [paper.published.strftime('%Y-%m-%d'), paper.entry_id, paper.title, shortsummary]

        # We create the csv file if it doesn't exist already
        if not os.path.exists(dirpath+paperlistfile):
            with open(dirpath+paperlistfile, "w", newline="") as f:
                writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["date_published", "url", "title", "summary"])

        # We insert each line as the second row in the file
        row_index = 1
        with open(dirpath+paperlistfile, "r+", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
            rows.insert(row_index, row)
            f.seek(0)
            writer = csv.writer(f)
            writer.writerows(rows)
