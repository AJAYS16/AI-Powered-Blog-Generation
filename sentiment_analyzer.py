import os
import logging
import re
import random
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-pro')

class SentimentAnalyzer:
    def __init__(self):
        """Initialize the sentiment analyzer"""
        # Blog style types
        self.style_types = {
            "professional": {
                "tone": "formal, authoritative, data-driven",
                "vocabulary": "industry-specific jargon, technical terms, sophisticated language",
                "structure": "well-structured with clear sections, bullet points, citations",
                "examples": "white papers, academic articles, technical documentation"
            },
            "casual": {
                "tone": "conversational, personable, engaging",
                "vocabulary": "everyday language, some industry terms, approachable explanations",
                "structure": "flowing paragraphs, stories, relatable examples",
                "examples": "lifestyle blogs, personal narratives, opinion pieces"
            },
            "simple": {
                "tone": "straightforward, clear, concise",
                "vocabulary": "common words, minimal jargon, plain language",
                "structure": "short paragraphs, simple explanations, direct points",
                "examples": "how-to guides, beginner tutorials, explanatory articles"
            }
        }
        
    def analyze_topic(self, topic):
        """
        Analyze a topic to determine the most appropriate blog style
        
        Args:
            topic (str): The blog topic
            
        Returns:
            str: Recommended blog style ('professional', 'casual', or 'simple')
        """
        try:
            # Clean the topic
            cleaned_topic = re.sub(r'[^\w\s]', '', topic.lower())
            
            # Keywords that suggest different styles
            professional_keywords = [
                'technical', 'analysis', 'research', 'enterprise', 'industry', 'infrastructure',
                'implementation', 'architecture', 'strategy', 'corporate', 'methodology',
                'framework', 'performance', 'optimization', 'protocol', 'standard', 'compliance'
            ]
            
            casual_keywords = [
                'experience', 'journey', 'story', 'life', 'personal', 'adventure', 'creative',
                'inspiration', 'lifestyle', 'trend', 'culture', 'perspective', 'thoughts',
                'reflections', 'opinion', 'review', 'recommendation'
            ]
            
            simple_keywords = [
                'guide', 'tutorial', 'how to', 'learn', 'beginners', 'introduction', 'basics',
                'simple', 'easy', 'step by step', 'explained', 'understand', 'quick', 'tips',
                'help', 'start', 'fundamental'
            ]
            
            # Count keyword occurrences
            prof_score = sum(1 for kw in professional_keywords if kw in cleaned_topic)
            casual_score = sum(1 for kw in casual_keywords if kw in cleaned_topic)
            simple_score = sum(1 for kw in simple_keywords if kw in cleaned_topic)
            
            # Determine highest score
            scores = {
                'professional': prof_score,
                'casual': casual_score,
                'simple': simple_score
            }
            
            # If there's a clear winner, return it
            max_score = max(scores.values())
            if max_score > 0:
                for style, score in scores.items():
                    if score == max_score:
                        return style
            
            # Default to professional if no clear match
            return 'professional'
            
        except Exception as e:
            logger.error(f"Error analyzing topic: {str(e)}")
            return 'professional'  # Default to professional as a fallback
    
    def analyze_with_ai(self, topic):
        """
        Use AI to analyze the appropriate blog style for a topic
        
        Args:
            topic (str): The blog topic
            
        Returns:
            dict: Analysis results with recommended style and explanation
        """
        try:
            prompt = f"""Analyze the following blog topic and determine the most appropriate writing style:

Topic: {topic}

Please classify the most suitable writing style among these options:
1. Professional: Formal, authoritative tone with industry jargon, technical terms, and structured format suitable for experts
2. Casual: Conversational, relatable tone with everyday language and flowing structure suitable for general audiences
3. Simple: Straightforward, clear tone with plain language and concise structure suitable for beginners

Return your response in this JSON format:
{{
  "recommended_style": "professional|casual|simple",
  "confidence_score": 0.0-1.0,
  "explanation": "Brief explanation of why this style is recommended",
  "topic_complexity": "high|medium|low",
  "target_audience": "Description of ideal audience"
}}"""

            response = model.generate_content(prompt)
            
            # Extract JSON from the response
            response_text = response.text
            # Find JSON content (between curly braces)
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                import json
                try:
                    result = json.loads(json_match.group(1))
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Error parsing JSON from AI response: {response_text}")
            
            # Fallback to simple parsing if JSON extraction fails
            if "professional" in response_text.lower():
                return {"recommended_style": "professional", "explanation": "AI recommended professional style"}
            elif "casual" in response_text.lower():
                return {"recommended_style": "casual", "explanation": "AI recommended casual style"}
            elif "simple" in response_text.lower():
                return {"recommended_style": "simple", "explanation": "AI recommended simple style"}
            else:
                return {"recommended_style": "professional", "explanation": "Default to professional style"}
                
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return {"recommended_style": "professional", "explanation": "Error occurred, defaulting to professional"}
    
    def get_style_prompt(self, style, topic):
        """
        Generate an appropriate prompt for the selected blog style
        
        Args:
            style (str): The blog style ('professional', 'casual', or 'simple')
            topic (str): The blog topic
            
        Returns:
            str: A prompt customized for the blog style
        """
        common_base = f"""Create a blog post about {topic}. """
        
        style_prompts = {
            "professional": f"""Write in a formal, authoritative tone suitable for industry professionals and experts. 
Use appropriate technical terminology, industry jargon, and sophisticated language. 
Structure the content with clear sections, headings, bullet points, and citations where applicable.
Include data points, technical specifications, and in-depth analysis.
The blog should be comprehensive, covering all technical aspects of the topic.""",
            
            "casual": f"""Write in a conversational, personable tone that engages general readers. 
Use everyday language with some industry terms that are explained in an approachable way.
Structure the content with flowing paragraphs, personal anecdotes, and relatable examples.
Include stories, opinions, and connect with the reader through shared experiences.
The blog should be engaging and interesting, making the reader feel connected to the topic.""",
            
            "simple": f"""Write in a straightforward, clear tone accessible to beginners and non-experts.
Use common words, minimal jargon, and plain language that anyone can understand.
Structure the content with short paragraphs, simple explanations, and direct points.
Include basic concepts, step-by-step instructions, and practical examples.
The blog should be easy to follow, focusing on fundamental understanding of the topic."""
        }
        
        # Get the appropriate style prompt or default to professional
        style_content = style_prompts.get(style, style_prompts["professional"])
        
        return common_base + style_content
    
    def adjust_blog_content(self, content, style):
        """
        Adjust existing blog content to match the desired style
        
        Args:
            content (str): Existing blog content
            style (str): Target style ('professional', 'casual', or 'simple')
            
        Returns:
            str: Adjusted blog content
        """
        try:
            prompt = f"""Rewrite the following blog content to match a {style} writing style:

Original Content:
{content[:2000]}  # Limit to first 2000 chars for the prompt

For a {style} style blog:
- Tone should be {self.style_types[style]['tone']}
- Vocabulary should use {self.style_types[style]['vocabulary']}
- Structure should be {self.style_types[style]['structure']}
- Similar to {self.style_types[style]['examples']}

Please rewrite the content maintaining all the key information but adjusting the style accordingly.
"""

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 1,
                    "top_k": 40,
                    "max_output_tokens": 4096,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error adjusting blog content: {str(e)}")
            return content  # Return original content if adjustment fails

# Test function
def test_sentiment_analyzer():
    analyzer = SentimentAnalyzer()
    
    test_topics = [
        "Technical Implementation of Kubernetes in Enterprise Environments",
        "My Journey Learning to Code: The Ups and Downs",
        "Beginner's Guide to Machine Learning: Simple Steps to Get Started"
    ]
    
    for topic in test_topics:
        # Rule-based analysis
        style = analyzer.analyze_topic(topic)
        print(f"Topic: {topic}")
        print(f"Rule-based analysis recommended style: {style}")
        
        # AI-based analysis
        ai_result = analyzer.analyze_with_ai(topic)
        print(f"AI analysis result: {ai_result}")
        
        # Get prompt for the style
        prompt = analyzer.get_style_prompt(style, topic)
        print(f"Generated prompt snippet: {prompt[:100]}...\n")

if __name__ == "__main__":
    test_sentiment_analyzer() 