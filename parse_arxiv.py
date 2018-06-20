import os
import requests
import numpy as np
import pandas as pd
import lxml.html as html
import smtp
import datetime

# TODO: используй arXiv API (https://github.com/zonca/python-parse-arxiv/blob/master/python_arXiv_parsing_example.py)
key_words = ["ballistic heat transfer", "scalar lattice", "thermal processes", "harmonic crystal", "kinetic temperature"]

domain_url = "https://arxiv.org"
url = "https://arxiv.org/list/physics/new"

response = requests.get(url)
page = html.fromstring(response.content)

links = page.find_class("list-identifier")
# TODO: раскидай по функциям
if response.status_code == 200:
    # successful connection

    print("-\nSuccessfull connection to {}".format(url))
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
                meta_info_text    = next(x.text.replace("\n", "") for x in meta_info_tags if x.attrib["class"] == "mathjax")

                links_children = link.getchildren()
                titles  = []
                authors = []

                # if contains(meta_info_text, key_words):
                if True:

                    abs_link = ""
                    pdf_link = ""

                    for meta_title in meta_info_titles:

                        titles.append(meta_title.tail.replace("\n", ""))

                    for meta_author in meta_info_authors:

                        authors.append(meta_author.text.replace("\n", ""))

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

                print("-\n{} submissions are found".format(index))
                break

    data["Title"]     = title_list
    data["Authors"]   = authors_list
    data["Abstracts"] = abstracts_list
    data["PDF"]       = pdf_list

    all_data_output_file = "arxiv.csv"
    new_data_output_file = "arxiv_new.csv"

    if not os.path.isfile(all_data_output_file):
        # if file does not exist write header
        data.to_csv(all_data_output_file, sep=";", mode="w", index=None)

    else:
        # else it exists so append without writing the header
        source_data = pd.read_csv(all_data_output_file, sep=";")

        # source and new data without suplicates
        whole_unique_data = source_data.append(data, ignore_index=True)\
            .drop_duplicates(subset=["Title", "Abstracts", "PDF"], keep='first')

        # only new data
        resulting_data = source_data.append(whole_unique_data, ignore_index=True)\
            .drop_duplicates(subset=["Title", "Abstracts", "PDF"], keep=False)

        number_of_res = resulting_data.shape[0]
        print("-\n{} NEW submissions".format(number_of_res))

        if number_of_res > 0:

            resulting_data.to_csv(all_data_output_file, sep=";", mode="a", header=False, index=None)
            resulting_data.to_csv(new_data_output_file, sep=";", mode="w", index=None)
            print("-\n.csv is successfully finished!")

            subject = "arXiv new articles " + datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S")
            smtp.send_mail("theormechipmm@mail.ru", ["theormechipmm@mail.ru"], subject, "", files=[new_data_output_file])
            print("-\n.email is successfully sent!")



else:
    # unsuccessful connection

    print("-\nConnection is failed to {}".format(url))