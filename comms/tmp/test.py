with open("finalTrains.txt", "r") as file:
	data = file.read()


longSplit = data.split('Longest:')
longest = longSplit[1].strip()
mostPips = longSplit[0].split('Most Pips:')[1].strip()
# mostPips = 0
print(longSplit)
print(longest, "\n", mostPips)

