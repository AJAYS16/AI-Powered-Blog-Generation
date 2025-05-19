# AI Blog Generator

A powerful blog generation tool with social media posting capabilities.

## Features

- **Content Research**: Automatically researches your topic using web scraping
- **Blog Generation**: Creates detailed blog posts using Gemini AI
- **Twitter Integration**: Includes recent tweets related to your topic
- **Tech-Savvy Image Generation**: Creates highly relevant AI-generated images, especially for technology topics
- **Sentiment Analysis**: Determines the appropriate blog style based on your topic
- **Multiple Blog Styles**: Choose between professional, casual, or simple writing styles
- **Social Media Integration**: Post your blogs directly to LinkedIn and Medium
- **DOCX Export**: Download your blog as a Word document

## Setup

1. Clone the repository
2. Install dependencies with `pip install -r requirements.txt`
3. Create a `.env` file based on `.env.example` with your API keys:
   - Gemini API Key
   - LinkedIn credentials
   - Medium API token
   - Stability AI API key
   - Twitter credentials (optional but recommended)

## Usage

Run the Streamlit interface:

```bash
streamlit run chatbot.py
```

## Blog Style Options

- **Professional**: Formal, technical, and detailed content with industry jargon and structured presentation
- **Casual**: Conversational and personal content that engages general readers
- **Simple**: Straightforward and clear content that's easy for beginners to understand

## Twitter Integration

The system will automatically:
- Search for recent tweets related to your blog topic
- Include 3 relevant tweets at the beginning of your blog
- Generate mock tweets if no real tweets are available

## Image Generation

- **Tech-Focused**: Special enhancements for technology topics, creating highly relevant images
- **Context-Aware**: Images match your blog's specific sections and content
- **High Quality**: Professional, clean aesthetics suitable for business blogs

## Social Media Posting

- **LinkedIn**: Post a summarized version of your blog with images
- **Medium**: Post the full blog as a draft on your Medium account

## Requirements

- Python 3.8+
- See requirements.txt for all dependencies

## Download sample output 
- [📄 Download Tesla Blog](Tesla_2025-05-17_23-28-48.docx)

