# coding: UTF-8

import re
import random
import string
from os import path, makedirs
from dragonmapper import transcriptions, hanzi
from urllib2 import urlopen, quote, HTTPError, Request

config = {
	'debug': False,
	'input': {
		'path': 'input/',
		'filenames': ['jaar1.txt', 'jaar2.txt'],
	},
	'output': {
		'path': 'output/',
		'filename': 'all.txt'
	},
	'audio': {
		'path': 'pronounciation/',
		'download': True,
		'url': 'http://tts.baidu.com/text2audio?lan=zh&ie=UTF-8&text=',
		'headers': {
			'Host': 'tts.baidu.com',
			'Referer': 'tts.baidu.com',
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
		}
	}
}

# Parse inputfiles
cards = []
for inputFilename in config['input']['filenames']:
	hashedCards = []
	with open(config['input']['path'] + inputFilename, 'r') as inputFile:
		tag = ''
		fileTag = re.sub(r'\.\w{3,}', '', inputFilename)

		for line in inputFile:
			hashedCards.append(line)
			line = line.strip()

			if len(line) == 0: continue
			if line[0] == '#': continue

			parts = line.split(';')
			if len(parts) == 1:
				tag = line.replace('\n', '')
			else:
				if len(parts[0]) == 32:
					cardID = parts.pop(0)
				else:
					hashedCards.pop(-1)
					cardID = ''.join(random.choice(string.lowercase + string.digits) for i in range(32))
					hashedCards.append(cardID + ';' + line + '\n')

				if len(parts) > 0:
					cardHanzis = []
					cardPinyins = []
					cardHanzi = parts.pop(0)
					cardHanzi = unicode(cardHanzi, 'utf-8')
					cardHanziParts = cardHanzi.split(',')
					for cardHanziPart in cardHanziParts:
						cardHanziPinyinParts = cardHanziPart.split(':')
						if len(cardHanziPinyinParts) == 2:
							cardHanzis.append(cardHanziPinyinParts.pop(0))
							cardPinyins.append(cardHanziPinyinParts.pop(0))
						else:
							cardHanzis.append(cardHanziPart)
							cardPinyins.append(hanzi.to_pinyin(cardHanziPart))

				if len(parts) > 0:
					cardTranslation = parts.pop(0)

				if len(parts) > 0:
					cardInfo = parts.pop(0).split(',')

				cards.append({ 'id': cardID, 'hanzi': cardHanzis, 'pinyin': cardPinyins, 'translation': cardTranslation, 'info': cardInfo, 'tag': tag, 'tags': [fileTag, tag] })

	with open(config['input']['path'] + inputFilename, 'w') as outputFile:
		for line in hashedCards:
			outputFile.write(line)

# Count different characters
chars = []
exclude = ['.', ' ', '?', '(', ')']
for card in cards:
	index = 0
	for cardHanzi in card['hanzi']:
		while index < len(cardHanzi):
			char = cardHanzi[index]
			if char not in chars:
				if char not in exclude:
					chars.append(char)
			index = index + 1
print 'Total of', len(chars), 'characters'

# Filter and merge duplicates
merges = []
filteredCards = []
filteredCardsByTag = {}
filteredCardsByIndex = {}
for cardIndex, card in enumerate(cards):
	uniqueCard = None
	for filteredCardIndex, filteredCard in filteredCardsByIndex.iteritems():
		if cardIndex > filteredCardIndex:
			if card['translation'] == filteredCard['translation']:
				for tag in card['tags']:
					if not tag in filteredCard['tags']:
						filteredCard['tags'].append(tag)
				for info in card['info']:
					if not info in filteredCard['info']:
						filteredCard['info'].append(info)

				for cardHanziIndex, cardHanzi in enumerate(card['hanzi']):
					if not cardHanzi in filteredCard['hanzi']:
						filteredCard['hanzi'].append(cardHanzi)
						filteredCard['pinyin'].append(card['pinyin'][cardHanziIndex])

				uniqueCard = filteredCard
			else:
				for cardHanzi in card['hanzi']:
					if cardHanzi in filteredCard['hanzi']:
						existingMerge = False
						for merge in merges:
							if merge['hanzi'] == cardHanzi:
								if merge['translation1'] == filteredCard['translation'] and merge['translation2'] == card['translation']:
									existingMerge = True
								elif merge['translation2'] == filteredCard['translation'] and merge['translation1'] == card['translation']:
									existingMerge = True
						if not existingMerge:
							merges.append({ 'hanzi': cardHanzi, 'translation1': filteredCard['translation'], 'translation2':  card['translation'] })

	del card['tag']
	if uniqueCard == None:
		filteredCards.append(card)
		filteredCardsByIndex[cardIndex] = card

	tag = ' - '.join(card['tags'])
	card = uniqueCard or card
	if tag in filteredCardsByTag:
		if not card in filteredCardsByTag[tag]:
			filteredCardsByTag[tag].append(uniqueCard or card)
	else:
		filteredCardsByTag[tag] = [uniqueCard or card]

if len(merges) > 0:
	for merge in merges:
		print 'Not merged because of different translations for', merge['hanzi']
		print '  1:', merge['translation1']
		print '  2:', merge['translation2']

# Download audio for cards if needed
audioPath = config['audio']['path']
if not path.exists(audioPath): makedirs(audioPath)

re1 = re.compile(r'\W', re.UNICODE)
for card in filteredCards:
	filenameParts = []
	for pinyin in card['pinyin']:
		filenamePart = transcriptions.accented_to_numbered(pinyin)
		filenamePart = re1.sub('', filenamePart)
		filenamePart = filenamePart.lower()
		filenamePart = filenamePart.encode(encoding='utf-8')
		filenameParts.append(filenamePart)
	filename = ''.join(filenameParts)

	card['sound'] = '[sound:' + filename + '.mp3]'

	if not path.exists(audioPath + filename + '.mp3'):
		if config['audio']['download']:
			hanzi = ','.join(card['hanzi'])
			url = config['audio']['url'] + quote(hanzi.encode(encoding='utf-8'))
			print 'Downloading sound for', hanzi
			try:
				response = urlopen(Request(url, headers=config['audio']['headers']))
				with open(audioPath + filename + '.mp3', 'wb') as f:
					f.write(response.read())
			except Exception as e:
				print 'Download failed for', hanzi
				print e
				exit()

# Colorify hanzi and pinyin
re1 = re.compile(r'\w', re.UNICODE)
re2 = re.compile(r'([^\W\d_]*)([0-5])', re.UNICODE)

for card in filteredCards:
	cardColorHanzi = []
	cardColorPinyin = []
	for pinyinIndex, pinyin in enumerate(card['pinyin']):
		pinyinTones = transcriptions.accented_to_numbered(pinyin).replace(u'ü', u'u').encode(encoding='utf-8')

		# colorify Hanzi
		if config['debug']:
			print card['hanzi'][pinyinIndex], pinyin, pinyinTones
		index = -1
		matches = re2.findall(pinyinTones)
		def colorifyHanzi(match):
			global index
			index += 1
			if config['debug']:
				print '*', index, match, match.group(0), matches[index]
			try:
				result = '<span class="tone' + matches[index][1] + '">' + match.group(0) + '</span>'
			except Exception as e:
				print 'Problem colorifying hanzi for', card['hanzi'][pinyinIndex], 'with', card['pinyin']
				exit()
			return result
		cardColorHanzi.append(re1.sub(colorifyHanzi, card['hanzi'][pinyinIndex]).encode(encoding='utf-8'))
		# colorify Pinyin
		start = 0
		result = ''
		for i, match in enumerate(re2.finditer(pinyinTones)):
			result += pinyin[start:match.start(0) - i]
			result += '<span class="tone' + match.group(2) + '">' + pinyin[match.start(0) - i:match.end(0) - 1 - i] + '</span>'
			start = match.end(0) - 1 - i
		result += pinyin[start:]
		cardColorPinyin.append(result.encode(encoding='utf-8'))
	card['hanzi'] = ', '.join(cardColorHanzi)
	card['pinyin'] = ', '.join(cardColorPinyin)

# Add markup to info and join tags
for card in filteredCards:
	card['tags'] = ' '.join(card['tags'])
	cardInfo = []
	for info in card['info']:
		cardInfo.append(info.replace(':', '<br>'))
	card['info'] = '<br><br>'.join(cardInfo)

# Write all output files
outputPath = config['output']['path']
if not path.exists(outputPath): makedirs(outputPath)

with open(outputPath + config['output']['filename'], 'w') as writeFile:
	for card in filteredCards:
		writeFile.write(card['id'] + ';' + card['hanzi'] + ';' + card['pinyin'] + ';' + card['translation'] + ';' + card['sound'] + ';' + card['info'] + ';' + card['tags'] + '\n')

for filename, cards in filteredCardsByTag.iteritems():
	with open(outputPath + filename + '.txt', 'w') as writeFile:
		for card in cards:
			writeFile.write(card['id'] + ';' + card['hanzi'] + ';' + card['pinyin'] + ';' + card['translation'] + ';' + card['sound'] + ';' + card['info'] + ';' + card['tags'] + '\n')
