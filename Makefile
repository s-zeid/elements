all:
	jekyll build

up:
	git commit --allow-empty-message -m ""
	git push origin master
