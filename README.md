# Cloud-project

### Project description
The project is a part of the Cloud Computing course at the Warsaw University of Technology. The project's goal is to create an application using GCP services; the rest is up to us. We decided to make a song recognition application. The user will be able to record a snippet of a song or upload a file, and the application will recognize the song and display the result. We want to recreate a simpler version of Shazam.

### Team members

- [Łukasz Lepianka](https://github.com/Luki308)
- [Mateusz Nizwantowski](https://github.com/nizwant)
- [Marta Szuwarska](https://github.com/szuvarska)

### Architecture

The architecture of the project is presented in the following diagram:

<img src="https://github.com/nizwant/Cloud-project/blob/main/deliverable/img/architecture.png" alt="crawling" width="700">

### Project requirements

There is an official list of requirements for the project in our group, but it is lackluster, so I will try to create a better one based on lectures and guidelines from previous years.

General requirements:

- UI
- Storage
- Terraform
- Large-scale assumption
- Rather Paas or Serverless than IaaS
- Queue (optional)
- Unit tests (optional)
- CI/CD
- Monitoring (optional)

We have to deliver a report and a presentation plan. The deadline is *28.04* (**Not for working application, just for plan of report and presentation**). The report should contain:

- Diagram with (micro)services and their connections  
- Design APIs (REST, RPC, GraphQL, …)
- Storage characteristics
  - Structured / unstructured
  - SQL / NoSQL
  - Strong / Eventual Consistency
  - Amount of Data
  - Read-only / Read & Write
  - …
- Terraform (working)
- SLA, SLO, SLI

### Products and services we use

This section covers only GCP services. The goal of this course is to learn about cloud computing, so we should use `serverless` services and not focus on `VMs`. Ideally, we should configure everything using `Terraform`. (It is a requirement)

- Cloud Run - dockerized applications
- Cloud Functions - seems like a good fit for processing requests to recognize songs, but I'm not sure yet
- App Engine - maybe for the simple web interface (I have read a blog about a comparison of this and cloud run, and the difference between cost was like 11$ vs 0.09$ for a month of usage, but there is more to this than meets the eye, and even if that is the case I would use App Engine just for the sake of testing it. It doesn't have to make sense)
- storage - Cloud SQL
- queuing - Pub/Sub
- load balancing - Cloud Load Balancing

Well, in theory, everything related to the compute can be done using Cloud Functions, but I'm not sure if it is a good idea. Even if it is, this project is about learning, so we should try to use more than one service to get to know them better and understand their pros and cons.

### Modules

- *algorithm* that finds similarity between audio tracks (core, this will take most of the time)
- *a web interface* that allows for recording of the audio (or adding it as a file) and transforms it into a simplified spectrogram. Then, query it against the dataset (how do you do it in the browser? You might as well send audio to the server, but it is expensive and ineffective. Also, privacy is a key factor). For sure, FFmpeg will be useful
- *crawler* that processes songs, so to simplify this step, I would use **static lists of the top 10000 songs of all time and a list of all Taylor Swift songs**, but then it needs to read them (from YouTube, I guess) and preprocess them and add it to the database
- *database* that stores crawled songs (it does not store the songs, only the fingerprint and the metadata - I think it might be relational db; maybe mongoDB idk how fingerprint looks like)
- *load balancing* in front (or proxy, not sure if we want to serve static content, most likely images of thumbnails or something like that)
- *cache layer* (maybe in front of the database) - I guess top songs cause the majority of traffic at a given period, but it brings complexity, and realistically speaking, we don't need it in this project, but if it would be serious, then it is a must. On the other hand, we have to compare songs against all songs in the database, so I don't know if there is a lot of benefit from caching

### User Capabilities

- record a snippet of a song with possible noise or add it as a file in a web browser
- show the match and player with a YouTube video of that song
- user should have the ability to add their songs (not mandatory, I think) - but this we should implement when we have time - maybe add a link from YouTube, and then it will work on this snippet; I think we will use it too when uploading songs from the data frames, there a are few options, for sure audio we will get from YouTube, but when it comes to metadata, we can use Spotify API, then user would need to pass title and artist, this would create a single interface for adding songs, or link to Spotify is even easier, but we might not have the data frame with this info so we would have to join ourselves

From the user's perspective, it seems simple, but in reality, it will be fairly complex.

### Some takeaways

1. Luckily, the core module can be implemented and tested independently; for example, we can test an algorithm using recorded by our phones samples of songs with different levels of background noise, export them, and compare them against 3-4 mp4 songs manually gathered from the internet, all of it can be stored inside git repo to simplify cooperation
2. Then we can extend this core functionality, and instead of manually scraping songs, we can automate this process and store it inside a database. If scraping will cost too much, we can do it locally and upload it (kinda hack, and I don't like it)
3. With this, we create a simple web UI that handles audio input and displays results; points 2 and 3 may switch in order

### How fingerprints are created

This procedure can be created using the following steps:

1. Get the audio file from YouTube (or any other source)
2. Convert it to a correct format (e.g., mp3, but I'm not sure what is correct for this task) using FFmpeg
3. Create a spectrogram from the audio file - I would not do it manually, but use some library for that (it probably exists)
4. Create a fingerprint from the spectrogram - this is the most crucial part, and I have no idea how to do it yet, but from what I read:
    - you have to reduce the quality of the spectrogram - this will reduce the size and thus increase the speed of processing and comparisons but also decrease noise to signal ratio, so the algorithm should be more accurate
    - reduce the frequency of the spectrogram to those that are used in songs - this will reduce the size of the fingerprint
    - process the spectrogram to create a scatter plot of the most important points
    - process somehow this scatter plot to create a fingerprint
5. Store the fingerprint in the database with metadata (e.g., song name, artist, etc.)

Truth be told, We're guessing there is a Python package that does all of this (maybe We're wrong), but We don't want to use it. On the other hand, We don't want to write it from scratch (because that is not the point), so there is a balance that we have to find.

### What happens when crawling (user wants to add a new song / new database of songs is added)

<img src="https://github.com/nizwant/Cloud-project/blob/main/deliverable/img/adding_new_songs.png" alt="crawling" width="700">

### What happens when the user wants to find what song it is

<img src="https://github.com/nizwant/Cloud-project/blob/main/deliverable/img/finding_what_song_it_is.png" alt="recognizing" width="900">

### What happens when the user wants to see what songs are in the database (optional but useful when debugging and grading)

<img src="https://github.com/nizwant/Cloud-project/blob/main/deliverable/img/list_available_songs.png" alt="listing" width="400">

### Unanswered questions

- do we need to implement authorization/authentication
- https or http is fine
- rate limiting
- monitoring
- how should we handle errors
