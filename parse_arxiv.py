import os
import requests
import numpy as np
import pandas as pd
import lxml.html as html
from pandas import DataFrame


key_words = ["ballistic heat transfer", "scalar lattice", "thermal processes", "harmonic crystal", "kinetic temperature"]

domain_url = "https://arxiv.org"
url = "https://arxiv.org/list/physics/new"

res = requests.get(url)
page = html.fromstring(res.content)

links = page.find_class("list-identifier")
info  = page.find_class("meta")

data = pd.DataFrame(columns=["Title", "Authors", "Abstracts", "PDF"])

title_list     = []
authors_list   = []
abstracts_list = []
pdf_list       = []

if len(links) != len(info):

    raise IndexError("Links and MetaInfo list sizes are different!")

else:

    for index, (link, meta_info) in enumerate(zip(links, info)):

        try:

            meta_info_tags = meta_info.getchildren()
            # first child HtmlElement with a "mathjax" class
            meta_info_titles  = next(x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-title mathjax")
            meta_info_authors = next(x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-authors")
            meta_info_text    = next(x.text for x in meta_info_tags if x.attrib["class"] == "mathjax")

            links_children = link.getchildren()
            titles  = []
            authors = []

            # if contains(meta_info_text, key_words):
            if True:

                for meta_title in meta_info_titles:

                    titles.append(meta_title.tail)

                for meta_author in meta_info_authors:

                    authors.append(meta_author.text)

                for elem in links_children:

                    # TODO: добавить try except
                    if elem.attrib["title"] == "Download PDF":

                        pdf_link = elem.attrib["href"]

                    elif elem.attrib["title"] == "Abstract":

                        abs_link = elem.attrib["href"]

            title_list.append("".join(titles))
            authors_list.append(", ".join(authors))
            abstracts_list.append(domain_url + abs_link)
            pdf_list.append(domain_url + pdf_link)

        except StopIteration:

            print("{} new submissions are finished!".format(index))
            break

data["Title"]     = title_list
data["Authors"]   = authors_list
data["Abstracts"] = abstracts_list
data["PDF"]       = pdf_list

output_file = "arxiv.csv"

if not os.path.isfile(output_file):
    # if file does not exist write header
    data.to_csv(output_file, sep=";", mode="w", index=None)
else:
    # else it exists so append without writing the header
    source_data = pd.read_csv(output_file, sep=";")

    # resulting_data = data.where(data.values != source_data.values, other=np.nan)
    resulting_data = source_data.append(data, ignore_index=True)
    resulting_data.drop_duplicates(subset=["Title"], keep=False, inplace=True)
    resulting_data.to_csv(output_file, sep=";", mode="w", index=None)
    # resulting_data.to_csv(output_file, sep=";", mode="a", header=False, index=None)

print(".csv is successfully finished!")