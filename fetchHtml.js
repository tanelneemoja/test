const axios = require('axios');
const fs = require('fs');

// URL of the website you want to scrape
const url = 'https://www.essencemediacom.ee';

axios.get(url)
  .then(response => {
    // Save the HTML to a file
    fs.writeFileSync('website.html', response.data);
    console.log('Website HTML fetched and saved!');
  })
  .catch(error => {
    console.error('Error fetching website HTML:', error);
  });
