up:
	docker compose up -d

clean:
	docker compose down

run:
	while true; do python ./main.py -s 1; sleep 1h; done

nuke: clean
	rm -rf data 
