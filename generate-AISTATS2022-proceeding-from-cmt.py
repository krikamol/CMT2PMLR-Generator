# %%
cmt_file = "aistats-cr-submissions.csv"
org_pdf_folder = "camera_ready/CameraReadys"
dest_pdf_folder = "dest_pdfs"

# %%
# imports
import pandas as pd
from shutil import copyfile, Error
import re
import os
from jinja2 import Environment, FileSystemLoader
from pylatexenc.latexencode import unicode_to_latex
import PyPDF2

# %%
# read in properties file from CMT
df = pd.read_csv(cmt_file, sep="\t")
df.rename(columns={"Q7 (Code release)": "Code"}, inplace=True)

# %%
# read in code urls that have been sent after the deadline
add_code_df = pd.read_csv("additional-code.csv")

for _, row in add_code_df.iterrows():
    df.loc[df["Paper ID"] == row["Paper ID"], "Code"] = row["Response"]

# %%
# a dictionary containing papers as dictionaries. Each paper must consist of
# (1) title
# (2) author (lastname, firstnames format separated by 'and')
# (3) pages in "startpage-endpage" format
# (4) abstract
# (5) code
papers = {}
identifiers = {}

YY = "22"
df["Key"] = ""
for index, row in df.iterrows():

    # read the paper information (paper id, title, authors, and abstract)
    paper_id = row["Paper ID"]
    title = row["Paper Title"].strip()
    authors = row["Author Names"].strip()
    abstract = row["Abstract"].strip()
    files = row["Files"].strip()
    code = row["Code"]

    # remove the newline character in the abstract
    abstract = " ".join(abstract.split())

    # extract filenames
    flist = list(filter(None, re.split(r"\(.*?bytes\);?", files)))
    flist = [f.strip() for f in flist]

    # preprocess the author names and extract the identifier (author's lastname)
    alist = list(filter(None, re.split(r"\(.*?\)\*?;?", authors)))
    alist = [a.strip() for a in alist]

    first_author_lastname = alist[0].split()[-1].title()
    paper_key = first_author_lastname + YY
    if first_author_lastname in identifiers:
        paper_key += chr(ord("a") + identifiers[first_author_lastname])
        identifiers[first_author_lastname] += 1
    else:
        identifiers[first_author_lastname] = 1

    # format the author list
    new_alist = []
    for i in range(len(alist)):
        new_alist.append(
            ", ".join([" ".join(alist[i].split()[1:]), alist[i].split()[0]])
        )
    new_alist = [a.title() for a in new_alist]
    author_list = " and ".join(new_alist)

    # add the paper to the dictionary
    papers[paper_key] = {
        "key": paper_key,
        "id": paper_id,
        "title": title,
        "authors": author_list,
        "files": flist,
        "software": code,
        "abstract": abstract,
    }
    df.loc[index, "Key"] = paper_key

for iden in papers:
    papers[iden]["new_files"] = [
        f.split("\\")[-1]
        for f in os.listdir("camera_ready/CameraReadys")
        if f.startswith(str(papers[iden]["id"]) + "\\")
    ]

# %%
# preprocess PDFs
not_enough_new_files = []
not_enough_files = []
errors = []


def copy_file(src, dest):
    try:
        copyfile(src, dest)
    except Error as err:
        errors.extend(err.args[0])


problematic_papers = {}
form_not_found = "permission form not found."
main_not_found = "main paper not found."
supp_not_found = "supplementary file may not exist."
multiple_supps = "multiple supplementary files."

for iden in papers:
    paper_id = papers[iden]["id"]
    main_paper = "{}.pdf".format(paper_id)
    supplement = "{}-supp".format(paper_id)
    perm_form = "{}-Permission.pdf".format(paper_id)

    # process main paper
    files_processed = 0
    if main_paper in papers[iden]["new_files"]:
        org_file = os.path.join(
            org_pdf_folder, "{}\CameraReady\{}".format(paper_id, main_paper)
        )
        files_processed += 1
    else:
        potential_main = [
            mf
            for mf in papers[iden]["new_files"]
            if any(subt for subt in ["main", "camera", "ready"] if subt in mf.lower())
        ]
        if any(potential_main):
            org_file = os.path.join(
                org_pdf_folder, "{}\CameraReady\{}".format(paper_id, potential_main[0])
            )
            files_processed += 1
        else:
            problematic_papers[iden] = main_not_found
            continue

    dest_file = os.path.join(dest_pdf_folder, "{}.pdf".format(iden))
    copy_file(org_file, dest_file)

    # process permission form
    if perm_form in papers[iden]["new_files"]:
        org_file = os.path.join(
            org_pdf_folder, "{}\CameraReady\{}".format(paper_id, perm_form)
        )
        files_processed += 1
    else:
        potential_form = [
            pf
            for pf in papers[iden]["new_files"]
            if any(
                subt
                for subt in ["permission", "pmlr", "agreement", "license"]
                if subt in pf.lower()
            )
        ]
        if any(potential_form):
            org_file = os.path.join(
                org_pdf_folder, "{}\CameraReady\{}".format(paper_id, potential_form[0])
            )
            files_processed += 1
        else:
            problematic_papers[iden] = form_not_found
            continue

    dest_file = os.path.join(dest_pdf_folder, "{}-Permission.pdf".format(iden))
    copy_file(org_file, dest_file)

    # process supplementary file
    supplement_file = [sf for sf in papers[iden]["new_files"] if supplement in sf]
    if any(supplement_file):
        if len(supplement_file) == 1:
            supplement_file = supplement_file[0]
            supp_ext = os.path.splitext(supplement_file)[1]
            org_file = os.path.join(
                org_pdf_folder, "{}\CameraReady\{}".format(paper_id, supplement_file)
            )
            files_processed += 1
            dest_file = os.path.join(
                dest_pdf_folder, "{}-supp{}".format(iden, supp_ext)
            )
            copy_file(org_file, dest_file)
        else:
            problematic_papers[iden] = multiple_supps
            continue

    else:
        potential_supp = [
            ps
            for ps in papers[iden]["new_files"]
            if any(
                subt
                for subt in ["sup", "supp", "supplementary", "appendix", "code"]
                if subt in ps.lower()
            )
        ]

        if any(potential_supp):
            supp_ext = os.path.splitext(potential_supp[0])[1]
            org_file = os.path.join(
                org_pdf_folder, "{}\CameraReady\{}".format(paper_id, potential_supp[0])
            )
            files_processed += 1
            # else:
            # problematic_papers[iden] = supp_not_found
            # continue

            dest_file = os.path.join(
                dest_pdf_folder, "{}-supp{}".format(iden, supp_ext)
            )
            copy_file(org_file, dest_file)
    if files_processed != len(papers[iden]["new_files"]):
        not_enough_new_files += [paper_id]
    if files_processed < len(papers[iden]["files"]):
        not_enough_files += [paper_id]

# %%
# print problrmatic papers
no_permission_form = [
    p for p in problematic_papers if problematic_papers[p] == form_not_found
]
no_main_paper = [
    p for p in problematic_papers if problematic_papers[p] == main_not_found
]
no_supplement = [
    p for p in problematic_papers if problematic_papers[p] == supp_not_found
]
multiple_supps = [
    p for p in problematic_papers if problematic_papers[p] == multiple_supps
]

print("Number of problematic papers: {}".format(len(problematic_papers)))
print("No permission form: {}".format(len(no_permission_form)))
print("No main paper: {}".format(len(no_main_paper)))
print("No supplementary: {}".format(len(no_supplement)))
print("Multiple supplements: {}".format(len(multiple_supps)))
print("Not enough files: {}".format(len(not_enough_files)))
print("Not enough new files: {}".format(len(not_enough_new_files)))

# what happened to missing papers
print("Problematic papers")
for key in problematic_papers:
    print(papers[key]["id"])

print("Papers with unmatched files")
[
    len(papers[k]["files"])
    for k in df.loc[df["Paper ID"].isin(not_enough_files)]["Key"].values
]  # .apply(len)

# %%
# count pages per paper
pages_count = 0
for f in os.listdir(dest_pdf_folder):
    if ("-" not in f) or (
        f
        in [
            "Cisneros-Velarde22.pdf",
            "Marteau-Ferey22.pdf",
            "Chérief-Abdellatif22.pdf",
            "Cohen-Addad22.pdf",
            "Nguyen-Duc22.pdf",
            "Duran-Martin22.pdf",
            "Tran-The22.pdf",
            "Cohen-Karlik22.pdf",
            "Bruns-Smith22.pdf",  # paper ids that are contain -
        ]
    ):
        file = open(dest_pdf_folder + "/" + f, "rb")
        readpdf = PyPDF2.PdfFileReader(file)
        paper_id = f.split(".")[0]
        papers[paper_id]["num_pages"] = readpdf.numPages

# %%
pages_count = 1
for _, row in df.iterrows():
    try:
        papers[row["Key"]]["pages"] = "{}-{}".format(
            pages_count, pages_count + papers[row["Key"]]["num_pages"] - 1
        )
        pages_count += papers[row["Key"]]["num_pages"]
    except KeyError:
        print(row["Key"])

# %%
# sanity check
print(
    "Number of pages: {}, Number of papers: {}, Ave pages per paper: {}".format(
        pages_count, len(papers), pages_count / len(papers)
    )
)

# %%
# encode special characters with latex commands
papers_new = {
    key: {
        k: unicode_to_latex(papers[key][k], non_ascii_only=True)
        for k in ["title", "authors", "software", "abstract", "pages"]
        if papers[key][k] == papers[key][k]
    }
    for key in papers
}

# %%
# Export the bibtex file
file_loader = FileSystemLoader("templates")
env = Environment(loader=file_loader)
template = env.get_template("bibtex_template.txt")
aistats22_bibtex = template.render(papers=papers_new)

f = open("aistats22.bib", "w")
f.write(aistats22_bibtex)
f.close()

# %%
# remove latex  \text*{} commands

with open("aistats22.bib", "r") as myfile:
    bibtex = myfile.read()

pat = "\\\\text([a-z].*?){(.*?)}"
bibtex = re.sub(pat, "\\2", bibtex)
bibtex = bibtex.replace("    software = {  }\n", "")

with open("aistats22.bib", "w") as myfile:
    myfile.write(bibtex)
