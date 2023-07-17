import re
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from rich import print

# to only process the first page
DEBUG = False


def main():
    with open("OHBM 2023 Schedule at a Glance.html", "r") as f:
        html_doc = f.read()

    c = Calendar()

    soup = BeautifulSoup(html_doc, "html.parser")

    sections = soup.find_all("section")

    date = None

    for page, section in enumerate(sections):
        if page == 0:
            continue

        if DEBUG and page > 1:
            break

        print(section.get("id"))

        paragraphs = section.find_all("p")

        times = get_times(paragraphs)
        print(times)

        if get_date(paragraphs) is not None:
            date = get_date(paragraphs)
        print(date)

        events = get_events(paragraphs)

        assert len(times) == len(events)

        for i in range(len(times)):

            name = events[i]["name"].replace("Morning ", "").replace("Afternoon ", "")

            begin, end = canonicalize_time(times[i])
            events[i]["begin"] = f"2023-07-{date}T{begin}-04:00"
            events[i]["end"] = f"2023-07-{date}T{end}-04:00"

            if not events[i].get("url"):
                events[i]["url"] = None

            if not events[i].get("location"):
                events[i]["location"] = None

            events[i]["description"] = f"{name}\n\n{events[i]['url']}" 

            # Uncomment to fetch the session description
            # if events[i]["url"]:
                # content = requests.get(events[i]["url"]).content
                # description_soup = BeautifulSoup(content, "html.parser")
                # events[i]["description"] = events[i]["url"]

            e = Event(
                name=events[i]["name"],
                begin=events[i]["begin"],
                end=events[i]["end"],
                location=events[i]["location"],
                url=events[i]["url"],
                description=events[i]["description"],
            )
            c.events.add(e)

        print(events)

    # save to a new file
    with open("OHBM_2023_clean.html", "w") as f:
        soup = soup.prettify()
        f.write(soup)

    with open("OHBM_2023.ics", "w") as f:
        f.writelines(c.serialize_iter())


def canonicalize_time(time):
    time = time.strip()

    begin = time.split("-")[0].split(":")
    begin = f"{int(begin[0]):02.0f}:{begin[1]}:00"

    end = time.split("-")[1].split(":")
    end = f"{int(end[0]):02.0f}:{end[1]}:00"
    if end in ["00:00:00", "01:00:00"]:
        end = "23:59:00"

    return begin, end


def get_events(paragraphs):
    events = []

    for i in range(len(paragraphs)):
        if not paragraphs[i].contents:
            continue
        value = paragraphs[i].contents[0].string

        if (
            value in ["Grand Quai", None, "TBD", "New City Gas"]
            or value.lower()
            in [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
            or is_time(value)
            or is_room(value)
            or is_date(value)
        ):
            continue

        if value == "LUNCH":
            event = {
                "name": value,
                "location": get_location(paragraphs, i),
            }
            events.append(event)
            continue

        if value == "BREAK":
            event = {
                "name": value,
            }
            events.append(event)
            continue

        event = {
            "name": value,
            "location": get_location(paragraphs, i),
            "url": get_url(paragraphs[i]),
        }
        events.append(event)

    return events


def get_name(p):
    return p.contents[0].string


def is_date(value):
    return value.startswith("JULY")


def get_date(paragraphs):
    for p in paragraphs:
        value = p.contents[0].string
        if is_date(value):
            date = value.split(" ")[1].replace(",", "")
            return date
    return None


def is_time(value):
    return re.match(r"\d{1,2}", value) if value else False


def get_times(paragraphs):
    times = []
    for p in paragraphs:
        value = p.contents[0].string
        if is_time(value):
            if ("-" not in value or value[-1] == "-") and len(p.contents) > 1:
                end_time = p.contents[1].string
                value = f"{value}{end_time}"
            if value[0] not in ["0", "1", "2"]:
                value = f"0{value}"
            if ":" in value and "-" in value:
                times.append(value)

    return times


def is_room(value):
    return re.match(r"\d{2,3}", value)


def get_location(paragraphs, i):
    if i + 1 >= len(paragraphs):
        return None
    name = get_name(paragraphs[i])
    value = paragraphs[i + 1].contents[0].string
    return f"room: {value}" if is_room(value) else None


def get_url(p):
    if p.contents[0].name != "a":
        return None
    encoded_link = p.contents[0].get("href")
    decoded_link = unquote(encoded_link)
    return decoded_link.replace(
        "https://ohbm-schedule-2023.my.canva.site/_link/?link=", ""
    )


if __name__ == "__main__":
    main()
