import streamlit as st
import os
from groq_scrapper import ContentScraper, generate_blog, save_blog_to_word
from image_generator import ImageGenerator
from sentiment_analyzer import SentimentAnalyzer
from social_scraper import SocialScraper
import tempfile
from pathlib import Path
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your AI Blog Generator. I can help you create professional blog posts. What topic would you like to write about?"}
        ]
    if 'blog_file' not in st.session_state:
        st.session_state.blog_file = None
    if 'scraper' not in st.session_state:
        st.session_state.scraper = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "topic"
    if 'blog_style' not in st.session_state:
        st.session_state.blog_style = None
    if 'blog_filepath' not in st.session_state:
        st.session_state.blog_filepath = None
    if 'sentiment_analyzer' not in st.session_state:
        st.session_state.sentiment_analyzer = SentimentAnalyzer()
    if 'social_scraper' not in st.session_state:
        st.session_state.social_scraper = SocialScraper(max_tabs=2)
    if 'generated_images' not in st.session_state:
        st.session_state.generated_images = []
    if 'social_content' not in st.session_state:
        st.session_state.social_content = {}

def generate_blog_with_images_and_social_content(topic, contents, include_images, blog_style='professional'):
    try:
        # Fetch relevant social media content for the topic (tweets, reddit posts, etc.)
        social_scraper = st.session_state.social_scraper
        
        with st.spinner("Fetching relevant social media content..."):
            social_content = social_scraper.fetch_social_content(topic, count=3)
            st.session_state.social_content = social_content
            
            # Count total posts found
            total_posts = sum(len(posts) for posts in social_content.values())
            logger.info(f"Fetched {total_posts} social media posts for topic: {topic}")
        
        # Generate blog content with appropriate style
        sentiment_analyzer = st.session_state.sentiment_analyzer
        style_prompt = sentiment_analyzer.get_style_prompt(blog_style, topic)
        
        # Modify the generate_blog function to use the style-specific prompt
        blog = generate_blog(topic, contents, style_prompt=style_prompt)
        
        if include_images:
            # Initialize image generator
            image_generator = ImageGenerator()
            # Generate images based on blog content
            with st.spinner("Generating AI images for your blog..."):
                generated_images = image_generator.generate_blog_images(
                    blog['content'],
                    num_images=2
                )
                blog['generated_images'] = generated_images
                # Store images in session state to prevent them from being lost
                st.session_state.generated_images = generated_images
        else:
            blog['generated_images'] = []
            st.session_state.generated_images = []
        
        # Add social content to the blog metadata
        blog['social_content'] = social_content
        
        # Add style information to the blog metadata
        blog['style'] = blog_style
        
        return blog
        
    except Exception as e:
        logger.error(f"Error in blog generation: {str(e)}")
        raise

def main():
    st.set_page_config(
        page_title="AI Blog Generator",
        page_icon="📝",
        layout="wide"
    )

    initialize_session_state()

    # Chat interface container
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    # User input and processing
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Process based on current step
        if st.session_state.current_step == "topic":
            # Save topic and analyze sentiment for style recommendation
            st.session_state.topic = prompt
            
            # Analyze topic to recommend a style
            with st.spinner("Analyzing your topic..."):
                analysis = st.session_state.sentiment_analyzer.analyze_with_ai(prompt)
                recommended_style = analysis.get("recommended_style", "professional")
                explanation = analysis.get("explanation", "Based on your topic")
            
            # Ask about blog style preference
            response = f"I'd recommend a {recommended_style} style for this topic. {explanation}\n\nWhich style would you prefer?\n1. Professional (formal, technical, detailed)\n2. Casual (conversational, personal, engaging)\n3. Simple (straightforward, clear, concise)"
            st.session_state.current_step = "style_choice"
            
        elif st.session_state.current_step == "style_choice":
            # Process style choice
            style_map = {
                "1": "professional", "professional": "professional",
                "2": "casual", "casual": "casual", 
                "3": "simple", "simple": "simple"
            }
            
            user_choice = prompt.lower().strip()
            # Match numbers or words
            if user_choice in style_map:
                blog_style = style_map[user_choice]
            else:
                # Default to professional if input not recognized
                blog_style = "professional"
                
            st.session_state.blog_style = blog_style
            
            # Ask about images
            response = f"I'll create a {blog_style} style blog for you. Would you like to include AI-generated images? Please reply with 'yes' or 'no'."
            st.session_state.current_step = "image_choice"
            
        elif st.session_state.current_step == "image_choice":
            # Process image choice
            user_response = prompt.lower().strip()
            include_images = user_response in ['yes', 'y', 'yeah', 'sure', 'true', '1']
            
            try:
                with st.spinner("Initializing blog generation..."):
                    # Initialize scraper if not already done
                    if not st.session_state.scraper:
                        st.session_state.scraper = ContentScraper()

                    # Research and generate content
                    with st.spinner("Researching your topic..."):
                        contents = st.session_state.scraper.generate_blog_content(st.session_state.topic)
                        
                    if not contents:
                        response = "I couldn't find enough information about this topic. Would you like to try a different topic? Please provide a new topic."
                        st.session_state.current_step = "topic"
                    else:
                        # Generate blog with selected style, social content, and images
                        with st.spinner(f"Generating your {st.session_state.blog_style} style blog{' with images' if include_images else ''}..."):
                            blog = generate_blog_with_images_and_social_content(
                                st.session_state.topic,
                                contents,
                                include_images,
                                blog_style=st.session_state.blog_style
                            )
                            
                            # Save blog to file
                            blog['topic'] = st.session_state.topic
                            filepath = save_blog_to_word(blog)
                            st.session_state.blog_filepath = filepath
                            
                            # Read the file content for download
                            with open(filepath, 'rb') as file:
                                st.session_state.blog_file = file.read()

                        # Create download button
                        st.download_button(
                            label="Download Blog (DOCX)",
                            data=st.session_state.blog_file,
                            file_name=f"blog_{st.session_state.topic.replace(' ', '_')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )

                        # Count total social posts fetched
                        total_social_posts = sum(len(posts) for platform, posts in st.session_state.social_content.items())
                        
                        # Ask about starting a new blog instead of social media posting
                        response = f"I've generated your blog with {total_social_posts} recent social media posts and{' ' + str(len(st.session_state.generated_images)) + ' images' if include_images else ' no images'}! You can download it using the button above. Would you like to create another blog? If yes, please provide a new topic."
                        st.session_state.current_step = "topic"

                        # Display social content preview
                        if st.session_state.social_content:
                            st.write("### Recent Social Media Content Included")
                            
                            # Show preview for each platform
                            for platform, posts in st.session_state.social_content.items():
                                if not posts:
                                    continue
                                    
                                platform_name = platform.capitalize()
                                if platform == "mock":
                                    platform_name = "Generated Content"
                                
                                st.write(f"**{platform_name}:**")
                                for i, post in enumerate(posts[:2]):  # Show max 2 posts per platform
                                    st.write(f"• {post['author']}: {post['text'][:100]}...")
                                    
                                st.write("---")

                        # Display image preview if images were generated
                        if include_images and st.session_state.generated_images:
                            st.write("### Preview Generated Images")
                            cols = st.columns(len(st.session_state.generated_images))
                            for idx, image_path in enumerate(st.session_state.generated_images):
                                try:
                                    if os.path.exists(image_path):
                                        cols[idx].image(image_path, caption=f"Generated Image {idx + 1}")
                                    else:
                                        cols[idx].error(f"Image {idx + 1} not found at {image_path}")
                                except Exception as e:
                                    cols[idx].error(f"Error displaying image {idx + 1}: {str(e)}")

            except Exception as e:
                response = f"An error occurred: {str(e)}. Would you like to try again? Please provide a new topic."
                st.session_state.current_step = "topic"
                logger.error(f"Error generating blog: {str(e)}")

        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)

if __name__ == "__main__":
    try:
        main()
    finally:
        # Clean up resources
        if 'scraper' in st.session_state and st.session_state.scraper:
            st.session_state.scraper.close()
        if 'social_scraper' in st.session_state and st.session_state.social_scraper:
            st.session_state.social_scraper.close()
