# 🔍 Twitter Data Search Engine with Couchbase + PostgreSQL  
**Master’s Project | Hybrid DBMS Architecture • High-performance Search • Caching & Indexing**

I built a production-style Twitter data search application that **integrates a NoSQL store (Couchbase Capella) with a relational database (PostgreSQL on AWS RDS)**, wrapped in a **Flask** web app. The system supports rich, multi-criteria search over ~100K tweets and users, with **LRU caching, TTL eviction, and aggressive indexing** to deliver millisecond-level responses.

---

## 🎯 What I set out to do
- Design a **scalable, cloud-hosted data platform** for semi-structured Twitter data
- **Model, persist, and query** data across **Couchbase (tweets)** and **PostgreSQL (users)**
- Deliver a **fast, user-facing search experience** with flexible filters and ranked results
- **Cut query latency drastically** through caching + indexing

---

## 🧱 System Architecture
**Datastores**
- **Couchbase Capella (NoSQL):** JSON tweet documents; queried with **N1QL**
- **PostgreSQL (AWS RDS):** normalized user profiles; joined via `user_id`

**Backend**
- **Flask** API serving search requests (keyword, hashtag, language, source, username, date range, or combinations)
- **Custom LRU Cache (Python):**  
  - Capacity-bound with **Least Recently Used** replacement  
  - **30-minute TTL** eviction + **hourly checkpointing** to JSON for persistence

**Indexing & Optimization**
- Secondary indexes on high-cardinality fields (tweet id, username, language, source, hashtags, creation date)
- Query translation layer to orchestrate Couchbase + PostgreSQL joins efficiently
---

## ⚡ Performance Wins
| Search Type     | No Cache  | With Cache | Speedup    |
|-----------------|-----------|------------|------------|
| Username        | 0.26 s    | 0.0005 s   | ~500×      |
| Text / Keyword  | 0.97 s    | 0.007 s    | ~138×      |
| Hashtag         | 1.9 s     | 0.0003 s   | ~6300×     |
| Language        | 0.465 s   | 0.003 s    | ~155×      |

Ranking logic prioritizes **recency, retweet count, and reply count**. I also surface **Top 10 Tweets (by retweets)** and **Top 10 Users (by tweet volume)**.

---

## 🧰 Tech Stack
**Python**, **Flask**, **Couchbase Capella (N1QL, SDK)**, **PostgreSQL (psycopg2, AWS RDS)**, **LRU Cache (custom)**, **JSON**, **Pandas** (for preprocessing)

---

## 🧠 Skills Demonstrated
- **Hybrid database architecture** (SQL + NoSQL) & cloud deployment
- **Schema / data model design**, JSON → relational mapping, attribute pruning
- **High-performance querying** (indexing, caching, TTL, persistence)
- **Full-stack backend engineering** with Flask
- **Search relevance & ranking design**
- **Scalable data ingestion** pipelines into Couchbase & PostgreSQL

---

## 🔎 Dataset
- **`corona-out-3` JSON dataset (~100K records)**
- Preprocessed to split tweet/user entities, extract hashtags, normalize dates, and introduce `retweet_id`

---

## 🚀 Future Extensions
- Add **full-text relevance scoring** (e.g., BM25) and semantic search
- Expose a **GraphQL API** for richer client integrations
- Containerize with **Docker** and orchestrate with **Kubernetes**
- Add **Prophet / ARIMA** modules to forecast tweet volumes or engagement
---
