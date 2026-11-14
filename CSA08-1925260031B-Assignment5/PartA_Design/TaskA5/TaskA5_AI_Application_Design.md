# TASK A5 – DESIGN AN AI APPLICATION FOR CITIZEN COMPLAINTS (4 Marks | K3 – Apply)

## A5.1 – Sentiment Scorer and Extractive Summariser (2 Marks)
### 1. Lexicon-Based Sentiment Scorer with Negation Handling
- **Lexicons:**
  - `POSITIVE = {"good", "clean", "fast", "helpful", "improved", "fresh", "clear", "safe"}` ($+1$ each)
  - `NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken", "smell", "dust", "cough", "toxic", "garbage", "burning"}` ($-1$ each)
  - `NEGATORS = {"not", "never", "no", "hardly", "barely"}`
- **Scoring Rule:** Tokenize lowercase words stripped of punctuation. Iterate through words at index $i$:
  - Look up base polarity $v \in \{+1, -1, 0\}$.
  - Check a 1-to-2 word lookback window (`words[i-1]` or `words[i-2]` when separated by an auxiliary verb like `"was"`/`"were"`): if a negator precedes the sentiment word, multiply polarity by $-1$ (e.g., `"not helpful"` $\rightarrow -1$; `"not bad"` $\rightarrow +1$).
  - Classify total score $S$: `positive` if $S > 0$, `negative` if $S < 0$, else `neutral`.

### 2. Frequency-Based Extractive Summariser
- **Algorithm:**
  1. Split the complaint corpus into individual sentences using regex (`re.split(r'(?<=[.!?])\s+', text)`).
  2. Tokenize words, convert to lowercase, and filter out common English **stopwords** (`{"the", "is", "in", "at", "and", "to", "a", "of", "for", "on", "with"}`).
  3. Compute word frequency $f(w)$ across all non-stopword tokens.
  4. Score each sentence $s_j$ by summing the frequencies of its important words normalized by sentence length (or raw sum capped to prevent bias toward run-on sentences): $\text{Score}(s_j) = \frac{\sum_{w \in s_j} f(w)}{\sqrt{|s_j|}}$.
  5. Select the top $k$ highest-scoring sentences in their original chronological order.

---

## A5.2 – Rule-Based Chatbot & Limitations (2 Marks)
### Architecture
1. **Intent & Entity Extraction:** Convert citizen query to lowercase and match keywords:
   - *Station Entity:* Match against known station names from the `stations` table (`adyar`, `guindy`, `anna nagar`, etc.).
   - *Metric Entity:* Match `pm2.5` / `pm25`, `pm10`, `no2`, or `temperature` / `temp`.
   - *Time Entity:* Match `today` (latest date in DB), `yesterday`, or explicit `YYYY-MM-DD` date via regex `\d{4}-\d{2}-\d{2}`.
2. **Parameterized SQL Execution:** Execute `SELECT pm25, day, hour FROM readings r JOIN stations s ON r.station_id = s.station_id WHERE LOWER(s.station_name) = ? ORDER BY r.day DESC, r.hour DESC LIMIT 1`.
3. **Template Response:** Format the retrieved numeric value with health advisory context (e.g., `"Latest PM2.5 in Adyar (2026-10-03 18:00) is 48.0 ug/m3 (Moderate)."`).

### Limitations of Rule-Based Chatbot
1. **Spelling & Typo Sensitivity:** Fails on typos (`"Adyarr"` or `"PM 2,5"`) unless fuzzy matching is added.
2. **No Multi-Turn Context:** Cannot resolve follow-up pronouns like `"What about yesterday?"` without session memory.
3. **Rigid Phrasing:** Struggles with complex comparative or causal questions (`"Why was the air worse near the industrial estate last Tuesday?"`).

---

## Algorithmic Pseudocode (SIMATS Engineering Standard)
```text
ALGORITHM ScoreSentimentWithNegation
INPUT: complaintText (string), posSet (set), negSet (set), negatorSet (set)
OUTPUT: label (string), totalScore (integer)

BEGIN
    SET cleanText <- REMOVE_PUNCTUATION(LOWERCASE(complaintText))
    SET words <- SPLIT(cleanText, " ")
    SET totalScore <- 0

    FOR i <- 0 TO LENGTH(words) - 1 DO
        SET w <- words[i]
        SET val <- 0
        IF w IN posSet THEN
            SET val <- 1
        ELSE IF w IN negSet THEN
            SET val <- -1
        ENDIF

        IF val != 0 AND i > 0 THEN
            IF words[i - 1] IN negatorSet THEN
                SET val <- -val
            ENDIF
        ENDIF
        SET totalScore <- totalScore + val
    ENDFOR

    IF totalScore > 0 THEN
        RETURN "positive", totalScore
    ELSE IF totalScore < 0 THEN
        RETURN "negative", totalScore
    ELSE
        RETURN "neutral", totalScore
    ENDIF
END
```

---

## Alternative Concept & Complexity Analysis
**Alternative Concept (Trained ML Model — Naive Bayes or Pre-Trained Transformer vs. Word List):**
If a trained machine-learning model (e.g., Multinomial Naive Bayes with TF-IDF, or a pre-trained DistilBERT classifier) is used instead of a static word list:
- **Solution Overview:**
  - *Naive Bayes:* Vectorizes complaint text via TF-IDF ($V$-dimensional sparse vector) and computes $P(y \mid x) \propto P(y)\prod_i P(x_i \mid y)$.
  - *Pre-trained Transformer (DistilBERT):* Passes subword tokens through 6 self-attention layers to capture contextual semantics, sarcasm, and domain-specific phrasing.
- **Comparison Table:**

| Dimension | Word-List Lexicon | Naive Bayes (TF-IDF) | Pre-Trained Transformer (DistilBERT) |
| :--- | :--- | :--- | :--- |
| **Time per Complaint** | **$O(L)$** (~$0.02\text{ ms}$ for $L$ words; pure hash lookups) | **$O(L)$** (~$0.15\text{ ms}$; sparse dot product) | **$O(L^2 \cdot d)$** (~$15\text{–}50\text{ ms}$ on CPU; self-attention matrix ops) |
| **Memory Needed** | **$< 10\text{ KB}$** (3 small Python `set` objects) | **$2\text{–}10\text{ MB}$** (vocabulary + log-likelihood matrix) | **$250\text{–}500\text{ MB}$** (model weights + tokenizer + runtime tensors) |
| **Expected Accuracy** | **70%–80%** (misses sarcasm, idioms, and out-of-lexicon complaints like *"thick black soot"*) | **82%–88%** (learns domain words like *"stagnant"*, *"effluent"*, *"wheezing"* from labeled data) | **91%–96%** (understands context, double negatives, and nuanced citizen grievances) |
