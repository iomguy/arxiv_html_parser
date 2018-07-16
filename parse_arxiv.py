import os
import requests
import pandas as pd
import lxml.html as html
import smtp
import datetime
from urllib.parse import urlparse


def number_of_inclusions(words_searched, text):
    """counts elements from substr_list that are included in main_str"""

    lowercase_text = text.lower()
    included_key_words = [s for s in words_searched if s.lower() in lowercase_text]
    number_of_included_key_words = len(included_key_words)
    return number_of_included_key_words, included_key_words


def form_data(page_content, csv_columns, domain, key_words_list):
    """creates a dataframe with new articles that include key_words in abstracts"""

    print("-\nSuccessful connection to {}".format(url))
    info = page_content.find_class("meta")

    submissions_data = pd.DataFrame(columns=csv_columns)

    title_list = []
    authors_list = []
    abstracts_list = []
    pdf_list = []
    included_key_words_list = []
    subject_list = []

    if len(links) != len(info):

        raise IndexError("Links and MetaInfo list sizes are different!")

    else:

        for index, (link, meta_info) in enumerate(zip(links, info)):

            try:

                meta_info_tags = meta_info.getchildren()
                # first child HtmlElement with a "mathjax" class
                meta_info_titles = next(
                    x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-title mathjax")
                meta_info_authors = next(
                    x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-authors")
                meta_info_subject = next(
                    x.getchildren() for x in meta_info_tags if x.attrib["class"] == "list-subjects")
                meta_info_primary_subject = next(
                    x for x in meta_info_subject if x.attrib["class"] == "primary-subject")
                meta_info_text = next(
                    x.text.replace("\n", "") for x in meta_info_tags if x.attrib["class"] == "mathjax")

                links_children = link.getchildren()
                titles = []
                authors = []
                subjects = []

                inclusions, included_key_words = number_of_inclusions(key_words_list, meta_info_text)

                if inclusions >= 2:

                    abs_link = ""
                    pdf_link = ""

                    for meta_title in meta_info_titles:
                        titles.append(meta_title.tail.replace("\n", ""))

                    for meta_author in meta_info_authors:
                        authors.append(meta_author.text.replace("\n", ""))

                    # TODO: добавить фильтр по соответствующим Subjects
                    subjects.append(meta_info_primary_subject.text.replace("\n", ""))
                    subjects.extend(meta_info_primary_subject.tail.replace("\n", "").split("; "))
                    subjects.remove("")

                    try:
                        # if authors is not empty and "Authors" is the first element
                        authors = authors[1:] if "Authors" in authors[0] else authors

                    except IndexError:

                        print("No-author article")

                    for elem in links_children:

                        # TODO: добавить try except
                        if elem.attrib["title"] == "Download PDF":

                            pdf_link = elem.attrib["href"]

                        elif elem.attrib["title"] == "Abstract":

                            abs_link = elem.attrib["href"]

                    title_list.append("".join(titles))
                    authors_list.append(", ".join(authors))
                    abstracts_list.append(domain + abs_link)
                    pdf_list.append(domain + pdf_link)
                    included_key_words_list.append(", ".join(included_key_words))
                    subject_list.append(", ".join(subjects))

            except StopIteration:

                print("-\n{} submissions found in total".format(index))
                break

        submissions_data["Title"] = title_list
        submissions_data["Authors"] = authors_list
        submissions_data["Abstracts"] = abstracts_list
        submissions_data["PDF"] = pdf_list
        submissions_data["Key_words"] = included_key_words_list
        submissions_data["Subjects"] = subject_list

        return submissions_data, index


def form_data_to_csv(data, csv_columns, all_data_output_file, new_data_output_file):

    if not os.path.isfile(all_data_output_file):
        # if file does not exist write header
        new_data = data
        pd.DataFrame(columns=csv_columns). \
            to_csv(all_data_output_file, sep=";", index=None)

    else:
        # else it exists so append without writing the header
        source_data = pd.read_csv(all_data_output_file, sep=";")

        # source and new data without duplicates
        whole_unique_data = source_data.append(data, ignore_index=True) \
            .drop_duplicates(subset=["Title", "Authors"], keep='first')

        # only new data
        new_data = source_data.append(whole_unique_data, ignore_index=True) \
            .drop_duplicates(subset=["Title", "Authors"], keep=False)

    number_of_res = data.shape[0]
    print("-\n{} submissions with key words found".format(number_of_res))

    number_of_new_res = new_data.shape[0]
    print("-\n{} NEW submissions with key words found".format(number_of_new_res))

    new_data.to_csv(all_data_output_file, sep=";", mode="a", header=False, index=None)
    new_data.to_csv(new_data_output_file, sep=";", mode="w", index=None)
    print("-\n.csv files are successfully finished!")

    return number_of_new_res, new_data_output_file


def send_mail(amount, attachment):
    """sends file to the email and attaches a file if amount is a nonzero int"""

    subject = "arXiv new articles " + datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S")
    text = "{0} NEW submissions with key words found. {1} submissions in total" \
        .format(amount, number_of_submissions_in_total)

    if amount > 0:

        file = [attachment]

    else:

        file = None

    smtp.send_mail("theormechipmm@mail.ru", ["theormechipmm@mail.ru"], subject, text, files=file)
    print("-\nemail is successfully sent!")


if __name__ == "__main__":
    # TODO: возможно, нужно будет использовать arXiv API:
    # https://github.com/zonca/python-parse-arxiv/blob/master/python_arXiv_parsing_example.py
    # Разделить слова по значимости (очевидно, что ключевые слова:
    # {амплитуда, период, температура, частота, корреляция, ковариация} встречаются почти в любой научной статье
    # Совпадению по таким словам стоит ставить меньший вес чем по остальным.

    with open("key_words.txt", "r", encoding="utf-8") as key_words_file:
        key_words = key_words_file.read().split("\n")

    with open("subjects.txt", "r", encoding="utf-8") as subjects_file:
        subjects = subjects_file.read().split("\n")

    columns = ["Title", "Authors", "Abstracts", "PDF", "Key_words", "Subjects"]
    whole_data_from_all_subjects = pd.DataFrame(columns=columns)
    number_of_submissions_in_total = 0

    for subject in subjects:

        url = "https://arxiv.org/list/{0}/new".format(subject)
        url_parsed = urlparse(url)
        url_domain = "://".join([url_parsed.scheme, url_parsed.netloc, url_parsed.path, url_parsed.query])
        print(url_parsed)
        response = requests.get(url)
        page = html.fromstring(response.content)

        links = page.find_class("list-identifier")

        if response.status_code == 200:
            # successful connection
            whole_data, number_of_submissions_in_total_in_subject = form_data(csv_columns=columns,
                                                                              page_content=page,
                                                                              domain=url_domain,
                                                                              key_words_list=list(set(key_words)))

            number_of_submissions_in_total += number_of_submissions_in_total_in_subject
            # TODO: статьи могут повторяться в разных subject'ах. number_of_submissions_in_total будет неверным

            whole_data_from_all_subjects = whole_data_from_all_subjects.\
                append(whole_data, ignore_index=True).\
                drop_duplicates(keep='first')

    else:
        # unsuccessful connection
        print("-\nConnection is failed to {}".format(url))

    new_results_amount, new_results = form_data_to_csv(whole_data_from_all_subjects,
                                                       csv_columns=columns,
                                                       all_data_output_file="arXiv.csv",
                                                       new_data_output_file="arXiv_new.csv")

    send_mail(new_results_amount, new_results)
