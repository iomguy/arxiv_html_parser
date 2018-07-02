import os
import requests
import numpy as np
import pandas as pd
import lxml.html as html
import smtp
import datetime


def number_of_inclusions(substr_list, main_str):
    """counts elements from substr_list that are included in main_str"""

    included_key_words = [s for s in substr_list if s in main_str]
    result = len(included_key_words)
    return result, included_key_words


def form_data(page_content, key_words_list):
    """creates a dataframe with new articles that include key_words in abstracts"""

    print("-\nSuccessful connection to {}".format(url))
    info = page_content.find_class("meta")

    submissions_data = pd.DataFrame(columns=csv_columns)

    title_list = []
    authors_list = []
    abstracts_list = []
    pdf_list = []
    included_key_words_list = []

    if len(links) != len(info):

        raise IndexError("Links and MetaInfo list sizes are different!")

    else:

        for index, (link, meta_info) in enumerate(zip(links, info)):

            try:
                meta_info_tags = meta_info.getchildren()
                # first child HtmlElement with a "mathjax" class
                meta_info_titles = next(
                    x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-title mathjax")
                meta_info_authors = next(x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-authors")
                meta_info_text = next(
                    x.text.replace("\n", "") for x in meta_info_tags if x.attrib["class"] == "mathjax")

                links_children = link.getchildren()
                titles = []
                authors = []

                inclusions, included_key_words = number_of_inclusions(key_words_list, meta_info_text)

                if inclusions >= 2:

                    abs_link = ""
                    pdf_link = ""

                    for meta_title in meta_info_titles:
                        titles.append(meta_title.tail.replace("\n", ""))

                    for meta_author in meta_info_authors:
                        authors.append(meta_author.text.replace("\n", ""))

                    try:
                        # if authors is not empty and "Authors" is the first element
                        authors = authors[1:] if "Authors" in authors[0] else authors

                    except:

                        print("No-author article")

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
                    included_key_words_list.append(",".join(included_key_words))

            except StopIteration:

                print("-\n{} submissions found in total".format(index))
                break

        submissions_data["Title"] = title_list
        submissions_data["Authors"] = authors_list
        submissions_data["Abstracts"] = abstracts_list
        submissions_data["PDF"] = pdf_list
        submissions_data["Key_words"] = included_key_words_list

        return submissions_data, index


if __name__ == "__main__":

    # TODO: используй arXiv API (https://github.com/zonca/python-parse-arxiv/blob/master/python_arXiv_parsing_example.py)
    # TODO: добавь нечувствительность к регистру
    key_words = ["ballistic heat transfer", "scalar lattice", "thermal processes", "harmonic crystal",
                 "kinetic temperature", "thermal"]
    csv_columns = ["Title", "Authors", "Abstracts", "PDF", "Key_words"]

    domain_url = "https://arxiv.org"
    url = "https://arxiv.org/list/physics/new"

    response = requests.get(url)
    page = html.fromstring(response.content)

    links = page.find_class("list-identifier")

    if response.status_code == 200:
        # successful connection

        data, number_of_submissions_in_total = form_data(page, key_words)

        all_data_output_file = "arXiv.csv"
        new_data_output_file = "arXiv_new.csv"

        if not os.path.isfile(all_data_output_file):
            # if file does not exist write header
            source_data = data
            new_data = data
            pd.DataFrame(columns=csv_columns).\
                to_csv(all_data_output_file, sep=";", index=None)

        else:
            # else it exists so append without writing the header
            source_data = pd.read_csv(all_data_output_file, sep=";")

            # source and new data without duplicates
            whole_unique_data = source_data.append(data, ignore_index=True)\
                .drop_duplicates(subset=csv_columns, keep='first')

            # only new data
            new_data = source_data.append(whole_unique_data, ignore_index=True)\
                .drop_duplicates(subset=csv_columns, keep=False)

        number_of_res = data.shape[0]
        print("-\n{} submissions with key words found".format(number_of_res))

        number_of_new_res = new_data.shape[0]
        print("-\n{} NEW submissions with key words found".format(number_of_new_res))

        new_data.to_csv(all_data_output_file, sep=";", mode="a", header=False, index=None)
        new_data.to_csv(new_data_output_file, sep=";", mode="w", index=None)
        print("-\n.csv files are successfully finished!")

        subject = "arXiv new articles " + datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S")
        text = "{0} NEW submissions with key words found. {1} submissions in total" \
            .format(number_of_new_res, number_of_submissions_in_total)

        if number_of_new_res > 0:

            file = [new_data_output_file]

        else:

            file = None

        smtp.send_mail("theormechipmm@mail.ru", ["theormechipmm@mail.ru"], subject, text, files=file)
        print("-\nemail is successfully sent!")

    else:
        # unsuccessful connection

        print("-\nConnection is failed to {}".format(url))
