import os
import sys
import argparse
import requests
import pandas as pd
import lxml.html as html
import smtp
import datetime
from urllib.parse import urlparse


def create_parser():
    # parsing named arguments from command line
    #
    # example:
    # python parse_arxiv -k key_words.txt -s subjects.txt

    args_parser = argparse.ArgumentParser(
        description='''arXiv new articles .html parser''',
        epilog='''(c) September 2018. Alexander Kalyuzhnyuk''')

    args_parser.add_argument('-k', '--keywords',
                             default=None,
                             help='Key words .txt file',
                             metavar='KEYWORDS',
                             type=str)

    args_parser.add_argument('-s', '--subjects',
                             default=None,
                             help='Subjects words/collocations .txt file',
                             metavar='SUBJECTS',
                             type=str)

    args_parser.add_argument('-e', '--email',
                             default=None,
                             help='send_from, send_to, server, port, login, password info .txt file',
                             metavar='EMAIL_INFO',
                             type=str)

    args_parser.add_argument('-a', '--all_output',
                             default=None,
                             help='name of the .csv file with all articles',
                             metavar='ALL_OUTPUT_FILENAME',
                             type=str)

    args_parser.add_argument('-n', '--new_output',
                             default=None,
                             help='name of the .csv file with new articles',
                             metavar='NEW_OUTPUT_FILENAME',
                             type=str)

    return args_parser


def number_of_inclusions(words_searched, text):
    """counts elements from substr_list that are included in main_str"""

    lowercase_text = text.lower()
    included_key_words = [s for s in words_searched if s.lower() in lowercase_text]
    number_of_included_key_words = len(included_key_words)
    return number_of_included_key_words, included_key_words


def form_data(page_content, csv_columns, domain, key_words_list):
    """creates a dataframe with new articles that include key_words in abstracts"""

    info = page_content.find_class("meta")

    submissions_data = pd.DataFrame(columns=csv_columns)
    title_list = []
    authors_list = []
    abstracts_list = []
    pdf_list = []
    included_key_words_list = []
    subject_list = []
    index = 0

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
                    x.text.replace("\n", " ") for x in meta_info_tags if x.attrib["class"] == "mathjax")

                links_children = link.getchildren()
                related_titles = []
                related_authors = []
                related_subjects = []

                inclusions, included_key_words = number_of_inclusions(key_words_list, meta_info_text)

                if inclusions >= 2:

                    abs_link = ""
                    pdf_link = ""

                    for meta_title in meta_info_titles:
                        related_titles.append(meta_title.tail.replace("\n", ""))

                    for meta_author in meta_info_authors:
                        related_authors.append(meta_author.text.replace("\n", ""))

                    # TODO: добавить фильтр по соответствующим Subjects
                    related_subjects.append(meta_info_primary_subject.text.replace("\n", ""))
                    related_subjects.extend(meta_info_primary_subject.tail.replace("\n", "").split("; "))
                    related_subjects.remove("")

                    try:
                        # if authors is not empty and "Authors" is the first element
                        related_authors = related_authors[1:] if "Authors" in related_authors[0] else related_authors

                    except IndexError:

                        print("No-author article")

                    for elem in links_children:

                        # TODO: добавить try except
                        if elem.attrib["title"] == "Download PDF":

                            pdf_link = elem.attrib["href"]

                        elif elem.attrib["title"] == "Abstract":

                            abs_link = elem.attrib["href"]

                    title_list.append("".join(related_titles))
                    authors_list.append(", ".join(related_authors))
                    abstracts_list.append(domain + abs_link)
                    pdf_list.append(domain + pdf_link)
                    included_key_words_list.append(", ".join(included_key_words))
                    subject_list.append(", ".join(related_subjects))

            except StopIteration:
                # no further items produced by the iterator "next" - in case of some articles with "Replacements"
                # -1 because the last index value relates to the first article with "Replacements"
                index -= 1
                break

        print("{} submissions found in total\n-".format(index + 1))

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
    print("{} submissions with key words found".format(number_of_res))

    number_of_new_res = new_data.shape[0]
    print("{} NEW submissions with key words found".format(number_of_new_res))

    new_data.to_csv(all_data_output_file, sep=";", mode="a", header=False, index=None)
    new_data.to_csv(new_data_output_file, sep=";", mode="w", index=None)
    print(".csv files are successfully finished!")

    return number_of_new_res, new_data_output_file, new_data


def send_mail(amount, text, attachment, email_info):
    """sends file to the email and attaches a file if amount is a nonzero int"""

    subject = "arXiv new articles " + datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S")
    text = "{0} NEW submissions with key words found. {1} submissions in total\n-{2}" \
        .format(amount, number_of_submissions_in_total, text)

    if amount > 0:

        file = [attachment]

    else:

        file = None

    smtp.send_mail(email_info["send_from"], [email_info["send_to"]], subject, text,
                   files=file,
                   server=email_info["server"],
                   port=email_info["port"],
                   login=email_info["login"],
                   password=email_info["password"]
                   )
    print("email is successfully sent!\n-")


if __name__ == "__main__":
    # TODO: возможно, нужно будет использовать arXiv API:
    # https://github.com/zonca/python-parse-arxiv/blob/master/python_arXiv_parsing_example.py
    # Разделить слова по значимости (очевидно, что ключевые слова:
    # {амплитуда, период, температура, частота, корреляция, ковариация} встречаются почти в любой научной статье
    # Совпадению по таким словам стоит ставить меньший вес чем по остальным.
    args_parser = create_parser()
    namespace = args_parser.parse_args(sys.argv[1:])  # sys.argv[0] is a script name

    if not namespace.keywords:
        print("You didn't input keywords file")

    elif not namespace.subjects:
        print("You didn't input subjects file")

    elif not namespace.email:
        print("You didn't input email info file")

    else:
        print("Beginning...")
        print("Using {} keywords".format(namespace.keywords))
        print("Using {} subjects".format(namespace.subjects))
        print("Using {} email file\n-".format(namespace.email))
        print("Using {} all output file".format(namespace.all_output))
        print("Using {} new output file-\n".format(namespace.new_output))

        email_info_dict = smtp.read_email_info(namespace.email)

        with open(namespace.keywords, "r", encoding="utf-8") as key_words_file:
            key_words = key_words_file.read().split("\n")

        with open(namespace.subjects, "r", encoding="utf-8") as subjects_file:
            subjects = subjects_file.read().split("\n")

        columns = ["Title", "Authors", "Abstracts", "PDF", "Key_words", "Subjects"]
        whole_data_from_all_subjects = pd.DataFrame(columns=columns)
        number_of_submissions_in_total = 0

        for subject in subjects:

            url = "https://arxiv.org/list/{0}/new".format(subject)
            print("Connecting to {}".format(url))
            url_parsed = urlparse(url)
            url_domain = "://".join([url_parsed.scheme, url_parsed.netloc])
            response = requests.get(url)
            page = html.fromstring(response.content)

            links = page.find_class("list-identifier")

            if response.status_code == 200:
                # successful connection
                # print("Connection is successful to {}".format(url))
                print("Success")
                whole_data, number_of_submissions_in_total_in_subject = form_data(csv_columns=columns,
                                                                                  page_content=page,
                                                                                  domain=url_domain,
                                                                                  key_words_list=list(set(key_words)))

                number_of_submissions_in_total += number_of_submissions_in_total_in_subject

                # drop duplicating papers
                whole_data_from_all_subjects = whole_data_from_all_subjects. \
                    append(whole_data, ignore_index=True). \
                    drop_duplicates(keep="first")

            else:
                # unsuccessful connection
                print("Connection is failed to {}\n-".format(url))

        new_results_amount, new_results, new_results_df = form_data_to_csv(whole_data_from_all_subjects,
                                                                           csv_columns=columns,
                                                                           all_data_output_file=namespace.all_output,
                                                                           new_data_output_file=namespace.new_output)

        # TODO: добавь проверку и ограничение на размер new_results_string в тексте сообщения
        if not new_results_df.empty:
            new_results_string = new_results_df.to_string(
                columns=["Title", "Key_words", "Key_words", "Authors", "Abstracts"],
                index_names=False,
                index=False)

        else:
            new_results_string = ""

        send_mail(amount=new_results_amount,
                  text=new_results_string,
                  attachment=new_results,
                  email_info=email_info_dict)
