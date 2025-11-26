Local Version
---

If you're interested in running this database locally for personal or research related endeavours, I have a locally run version made for that.

To populate the database, run 
```bash
python3 generator.py
```
This will populate continuously populate the database until interrupted. If it's ran when a database is already present, it will continue at the latest entry.

To access the GUI interface, run
```bash
./startup.sh
```
It will run the server.py file and then navigate to the locally hosted webpage. At any moment you can stop it by pressing any key.

Web Version
---
If you want to locally run the web version (why?), then you can do that too. The way that I locally test it is by running
```bash
python3 -m http.server
```
and then navigating to [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

-# try and figure out why I use 47274 in the local version!
