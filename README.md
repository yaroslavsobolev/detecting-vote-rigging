# Анализ электоральных фальсификаций на "общенародном голосовании" 1 июля 2020 в России 
Using data analysis to detect electoral fraud in 2020 referendum on constitutional amendments in Russia

Смысл и подробности этого анализа описаны в 
[этом посте](https://yaroslavsobolev.github.io/pages/project/2020-vote-rigging-in-russia-during-constitutional-referendum).

Файл `results.7z` должен быть распакован. Это даст файт `results.txt`, который содержит официальные результаты 
общенародного голосования с сайта ЦИК.

Файл базы данных SQLite `сik.sqlite` с адресами всех УИК следует скачать c
 [репозитория Gis-lab](https://gis-lab.info/qa/cik-data.html) по вот
  [этой ссылке](http://gis-lab.info/data/cik/cik_20200628.7z) 
  и распаковать. 
  
Скрипт `analysis.py` собственно и делает главное дело — ищет нужные УИКи и рисует картинки, 
показанные в 
[посте](https://yaroslavsobolev.github.io/pages/project/2020-vote-rigging-in-russia-during-constitutional-referendum). 