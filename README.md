# Cloud-project

### Modules
- *algorithm* that finds similarity between audio tracks (core, this will take most of the time) 
- *a web interface* that allows for recording of the audio (or adding it as a file) and transforms it into a simplified spectrogram. Then, query it against the dataset (how do you do it in the browser? You might as well send audio to the server, but it is expensive and ineffective. Also, privacy is a key factor). For sure, FFmpeg will be useful 
- *crawler* that processes songs, so to simplify this step, I would use **static lists of the top 1000 songs of all time and a list of all Tylor Swift songs**, but then it needs to read them (from YouTube, I guess) and preprocess them and add it to the database
- *database* that stores crawled songs (it does not store the songs, only the fingerprint and the metadata - I think it might be relational db; maybe mongoDB idk how fingerprint looks like)
- *load balancing* in front (or proxy, not sure if we want to serve static content, most likely images of thumbnails or something like that)
- *cache layer* (maybe in front of the database) - I guess top songs cause the majority of traffic at a given period, but it brings complexity, and realistically speaking, we don't need it in this project, but if it would be serious, then it is a must

### User Capabilities
- record a snippet of a song with possible noise or add it as a file in a web browser
- show the match and player with a YouTube video of that song 
- user should have the ability to add their songs (not mandatory, I think) - but this we should implement when we have time - maybe add a link from YouTube, and then it will work on this snippet 

From the user's perspective, it seems simple, but in reality, it will be fairly complex.

### Some takeaways 
1. Luckily, the core module can be implemented and tested independently; for example, we can test an algorithm using recorded by our phones samples of songs with different levels of background noise, export them, and compare them against 3-4 mp4 songs manually gathered from the internet, all of it can be stored inside git repo to simplify cooperation 
2. Then we can extend this core functionality, and instead of manually scraping songs, we can automate this process and store it inside a database. If scraping will cost too much, we can do it locally and upload it (kinda hack, and I don't like it)
3. With this, we create a simple web UI that handles audio input and displays results; points 2 and 3 may switch in order

### How fingerprints are created
`TODO`

### What happens when crawling
`TODO`

### What happens when the user wants to find what song it is
`TODO`

### What happens when the user wants to add a new song
`TODO`

### What happens when the user wants to see what songs are in the database (optional but useful when debugging and grading)
`TODO`


### Unanswered questions
- do we need to implement authorization/authentication 
- https or http is fine
- rate limiting 
- monitoring 
- how should we handle errors
