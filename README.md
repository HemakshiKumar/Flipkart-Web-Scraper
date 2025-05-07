# Flipkart Product Scraper & Best Match Selector
This Jupyter Notebook is designed to scrape product listings from Flipkart based on a user-defined search query (e.g., Bluetooth headset), extract detailed product information, and intelligently determine the best match based on rating and review metrics.

⚠️ Note: As of now, this script no longer works because Flipkart has changed its website structure. The HTML elements used to extract data are no longer valid and need to be updated for the scraper to function correctly.

📌 Features
- Sends HTTP requests to Flipkart's search result pages.
- Parses HTML using BeautifulSoup to extract:
  Product names
  Prices
  Ratings
  Number of reviews
- Compiles the extracted data into a Pandas DataFrame.
- Predicts the best product match using a weighted scoring formula based on rating and review count.
- Exports all collected data to a clean, structured CSV file for further analysis.

Example Output:
Product Name	Price	Rating	Reviews
ABC Headset	₹1,299	4.3	8,210
XYZ Earbuds	₹999	4.5	3,000

Best Match Prediction: ABC Headset (based on balanced rating and review count)

How "Best Match" Is Predicted
The best product match is selected using a custom ranking strategy that favors:
- High product ratings
- A substantial number of reviews (for reliability)
- This helps avoid overrating products with very few votes.

Requirements:
Install the required Python libraries:
- pip install requests beautifulsoup4 pandas

How to Use
- Open the notebook using Jupyter Notebook or JupyterLab.
- Copy-paste the link flipkart search to the code.
- Run each cell step by step.
- Check the final DataFrame and the best match prediction.
- View or download the output CSV file.

⚠️ Limitations & Disclaimer
Flipkart uses dynamic content loading and anti-bot mechanisms. The HTML structure changes frequently, which breaks static scrapers.
To fix this, you must inspect the current Flipkart page in your browser and update the HTML tags/classes accordingly.
This tool is for educational and personal use only. Always comply with a website’s Terms of Service when scraping.

