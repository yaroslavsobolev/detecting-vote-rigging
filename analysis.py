import numpy as np
import sqlite3
import pickle
import re
import matplotlib.pyplot as plt

# These are UIKs that were chosen by me manually after looking through the images of all UIKs
# These ID numbers are not official ID number of UIKs. These are indices internal to this script only. These indices
# correspond to the output image file names, e.g. "123.png"
shady_uiks = [84, 115, 149, 155, 195, 259,
              355, 528, 553, 578, 607, 618, 631, 635, 643, 775, 782, 783, 821, 868, 878, 1091, 1172, 1273, 1294,
              2331, 2372, 2398, 2521, 2553, 2713, 2833, 2854, 2871, 3482, 3575, 4019, 4352, 4459, 5175, 5216,
              5262, 5266, 5312, 5355, 5880, 5883, 5885, 5886, 5887, 5900, 5901, 5902, 5908, 6032, 6034, 6039, 6049,
              6083, 6094, 6100, 6205]

# These are Github Markdown files that I later used for organizing the output
md_file   = open("shady_uiks_md/readme.md","w+", encoding='utf8')
post_file = open("shady_uiks_md/post_file.md","w+", encoding='utf8')

# The 'results.txt' was initially produced by crawlers of official CIK website. Crawlers were written Sergei Shpilkin.
data = np.genfromtxt('results.txt', delimiter='\t', dtype=None, usecols=[1,2,3,4,5,6,7,8,9,10],
                     encoding='utf8', skip_header=1,
                     names=('reg', 'tik', 'uik', 'voters_total', 'ballots_issued', 'ballots_in_box',
                            'invalid_ballots', 'yes', 'no', 'url'))
# Find a list of unique regions
unique_regs = sorted(list(set([x['reg'] for x in data])))

# This is a table of region's latin name from "results.txt" and region's Cyrillic name from cik.sqlite database
# I made this conversion table manually and then I load it here.
conversion_list = np.genfromtxt('conversion_list_1.txt', dtype=None, delimiter='\t', usecols=[1], encoding='utf8')

# The conversion table is printed for debugging purposes: just to make sure that the conversion table is correct.
for i, reg in enumerate(unique_regs):
    print('{0} >>> {1}'.format(reg, conversion_list[i]))

# Conversion table is organized into two dictionaries that serve as converters: they convert between latin and cyrillic
# names of the region.
lat_to_rus = dict()
rus_to_lat = dict()
for i, rus in enumerate(unique_regs):
    lat = conversion_list[i]
    lat_to_rus[lat] = rus
    rus_to_lat[rus] = lat

# Regular expression used to find the UIK number in a string
find_uik_id = re.compile('(\d+)')

# Voting results are reorganized into sections by the region (федеральный округ)
# Data is stored as nested dictionaries: data_by_regs[region][uik_id]
data_by_regs = dict()
for d in data:
    uik_id = re.findall(find_uik_id, d['uik'])
    if uik_id:
        uik_id = int(uik_id[0])
    if d['reg'] not in data_by_regs.keys():
        data_by_regs[d['reg']] = {uik_id: d}
    else:
        data_by_regs[d['reg']][uik_id] = d

# Dumped to pickle file for future use
pickle.dump( data_by_regs, open( "data_by_regs.p", "wb+" ) )

# Файл базы данных SQLite `сik.sqlite` с адресами всех УИК следует скачать c
#  [репозитория Gis-lab](https://gis-lab.info/qa/cik-data.html) по вот
#   [этой ссылке](http://gis-lab.info/data/cik/cik_20200628.7z)
#   и распаковать.
conn = sqlite3.connect('cik.sqlite')
cursor = conn.cursor()

# find UIKs with identical addresses
cursor.execute('SELECT address_voteroom, COUNT(*) c FROM cik_uik GROUP BY address_voteroom HAVING c > 1')
data = cursor.fetchall()
addresses = [x[0] for x in data]

# find UIKs with a given address and plot their voting data
address = addresses[1]
for address_id, address in enumerate(addresses[1:]):
    # Skip if the address_id is not in the list I made manually. Comment out this IF statement and "continue"
    # directive if you want to generate output images for more UIKs
    if address_id not in shady_uiks:
        continue
    # Find all UIKs that have a given address
    sqlite_query = "SELECT id, region, name, address_voteroom, url FROM cik_uik WHERE address_voteroom='{0}'".format(
        address)
    cursor.execute(sqlite_query)
    target = cursor.fetchall()
    vote_data = []
    voting_data_found = False
    cik_urls = []
    for t in target:
        _, reg, name, addr, url = t
        uik_id = re.findall(find_uik_id, name)
        if uik_id:
            uik_id = int(uik_id[0])
        try:
            voting_results = data_by_regs[lat_to_rus[reg]][uik_id]
        except KeyError:
            print('Voting data not found for: {0}'.format(uik_id))
            voting_data_found = False
            break

        voting_data_found = True
        vote_data.append([uik_id, voting_results['voters_total'], voting_results['yes'], voting_results['no']])
        cik_urls.append([url, voting_results['url']])

    # If one the the UIKs at this address did not participate in the 20202 July 1st voting, skip the entire address
    # and move to the next one
    if not voting_data_found:
        continue

    # Convert to numpy format
    vote_data = np.array(vote_data)

    # skip if no votes are larger than 1000
    if np.all(vote_data[:, 2] < 1000) and (np.all(vote_data[:, 3] < 1000)):
        print('skipping since no UIKs at this address exceed 1000 "YES" votes')
        continue

    # Considered vote corrections. The last 1000 votes should only be illustrated for UIKs that have more "YES" votes
    # than their neighbours. Here I select which UIKs merit this illustration. My conditions are:
    #   1. Number of "YES" votes on this UIK must exceed 1050
    #   2. "YES" must exceed 70% of all votes (all ballots)
    #   3. Turnout (явка) must exceed 0.5
    # All three conditions must be met by a UIK for the 1000 votes to be highlighted.
    corrections = []
    for i in range(vote_data.shape[0]):
        if (vote_data[i, 2] > 1050) and ((vote_data[i, 2] / (vote_data[i, 2] + vote_data[i, 3])) > 0.7) and \
                (((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1]) > 0.5):
            corrections.append(1000)
        else:
            corrections.append(0)
    corrections = np.array(corrections)

    # This means the relative number of "NO" votes
    no_vote_percentage = vote_data[:, 3] / vote_data[:, 1]

    # The following part of code looks complex, but it's only for serving the "barplot" method. The barplot method
    # obeys a logic that is not very convenient (I mean, not very convenient for our purposes here).
    corrected_values = ((vote_data[:, 2] - corrections) / (vote_data[:, 1]))
    real_yes_minus_corrected = ((vote_data[:, 2] + vote_data[:, 3]) / vote_data[:, 1]) - (corrected_values + no_vote_percentage)

    fig, ax = plt.subplots(figsize=(8, 0.8+0.8*vote_data.shape[0]))
    ind = np.arange(len(target))
    width = 0.4
    ax.barh(ind, vote_data[:, 3] / vote_data[:, 1], color='C0', height=width)

    ax.barh(ind, corrected_values, left=no_vote_percentage, color='C1', height=width, alpha=1)
    ax.barh(ind, real_yes_minus_corrected, left=(corrected_values + no_vote_percentage), color='C1', height=width, alpha=0.6)
    ax.barh(ind,
            1-(real_yes_minus_corrected + corrected_values + no_vote_percentage),
            left=(real_yes_minus_corrected + corrected_values + no_vote_percentage), color='grey', height=width,
            alpha=0.3)

    for i in range(vote_data.shape[0]):
        ax.text(0.5*(1 + ((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1])),
                ind[i]-0.05,
                'неявка', fontsize=10,
                ha='center')

    ax.set_xlim(0,1)
    ax.set_ylim(0-width, ind[-1]+width*1.5)
    ax.set_yticks(ind)
    ax.set_xticks([])
    ax.set_yticklabels(['УИК \n№{0}'.format(v) for v in vote_data[:,0].astype(np.int)])
    ax.set_title(address, fontsize=11, wrap=True)
    for location in ['top', 'bottom', 'left', 'right']:
        ax.spines[location].set_visible(False)

    # Plotting various arrows
    def annotate_dim(ax, xyfrom, xyto, text=None, deltay=0.05):
        if text is None:
            text = str(np.sqrt((xyfrom[0] - xyto[0]) ** 2 + (xyfrom[1] - xyto[1]) ** 2))
        ax.annotate("", xyfrom, xyto, arrowprops=dict(arrowstyle='<->'))
        ax.text((xyto[0] + xyfrom[0]) / 2, (xyto[1] + xyfrom[1]) / 2 + deltay, text, fontsize=8, ha='center')

    stretch_value = 0.005
    # This is all for drawing arrows on the plots. The logic here is more intricate than necessary.
    for i in range(vote_data.shape[0]):
        annotation_height = ind[i]+width/2 + 0.05
        annotate_dim(ax=ax, xyfrom=[0,
                                    annotation_height],
                     xyto=[(vote_data[i, 3] / vote_data[i, 1]) + stretch_value,
                            annotation_height],
                     text='"Нет"\n{0}'.format(int(vote_data[i, 3]),
                                                   100*vote_data[i, 3] / (vote_data[i, 2] + vote_data[i, 3])))
        if vote_data[i, 2] / vote_data[i, 1] > 0.2:
            annotate_dim(ax=ax, xyfrom=[(vote_data[i, 3] / vote_data[i, 1]) - stretch_value,
                                annotation_height],
                         xyto=[((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1]) + stretch_value,
                                annotation_height],
                         text='"Да"\n{0} ({1:.0f}% от явки)'.format(int(vote_data[i, 2]),
                                                       100*vote_data[i, 2] / (vote_data[i, 2] + vote_data[i, 3])))
        elif vote_data[i, 2] / vote_data[i, 1] > 0.13:
            annotate_dim(ax=ax, xyfrom=[(vote_data[i, 3] / vote_data[i, 1]) - stretch_value,
                                annotation_height],
                         xyto=[((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1]) + stretch_value,
                                annotation_height],
                         text='"Да"\n{0}\n({1:.0f} от явки)'.format(int(vote_data[i, 2]),
                                                       100*vote_data[i, 2] / (vote_data[i, 2] + vote_data[i, 3])))
        else:
            annotate_dim(ax=ax, xyfrom=[(vote_data[i, 3] / vote_data[i, 1]) - stretch_value,
                                annotation_height],
                         xyto=[((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1]) + stretch_value,
                                annotation_height],
                         text='"Да"\n{0}\n({1:.0f}%)'.format(int(vote_data[i, 2]),
                                                       100*vote_data[i, 2] / (vote_data[i, 2] + vote_data[i, 3])))
        if corrections[i] > 0:
            annotation_height = ind[i] - width / 2 + 0.05
            annotate_dim(ax=ax, xyfrom=[corrected_values[i] + no_vote_percentage[i] - stretch_value,
                                annotation_height],
                         xyto=[((vote_data[i, 2] + vote_data[i, 3]) / vote_data[i, 1]) + stretch_value,
                                annotation_height],
                         text='1000 голосов')

    plt.subplots_adjust(top=0.73, bottom=0.001)
    fig.savefig('figures/shady_uiks/{0}.png'.format(address_id), dpi=200)
    plt.close(fig)

    # This part is writes GitHub Markdown files for organizing the plots nicely -- so that the URL to data source
    # would be below every plot.
    string_here = ''
    voting_string = ''
    for i in range(vote_data.shape[0]):
        voting_string += '[УИК №{0}]({1}) | '.format(int(vote_data[i, 0]), cik_urls[i][1])
    people_string = ''
    for i in range(vote_data.shape[0]):
        people_string += '[УИК №{0}]({1}) | '.format(int(vote_data[i, 0]), cik_urls[i][0])
    string_here = 'Ссылки на официальный сайт ЦИК: Результаты голосования ({0}). Адрес и члены комиссий ({' \
                  '1})\n\n\n'.format(voting_string[:-3], people_string[:-3])
    print(string_here)
    post_file.write('\n![](/pages/images/vote_rigging_1/locations/uiks/{0}.png)\n\n'.format(address_id) + \
                    string_here)
    md_file.write('\n![](https://yaroslavsobolev.github.io/pages/images/vote_rigging_1/locations/uiks/{'
                                '0}.png)\n\n'.format(
        address_id) + string_here)

md_file.close()
post_file.close()

