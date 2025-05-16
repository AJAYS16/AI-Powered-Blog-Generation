import io
from PIL import Image
import re
import os
import time
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client
import warnings
import logging
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        self.base_dir = r"E:\twitter content generation\twitter_blog_project\generated_images"
        self.blog_dir = os.path.join(self.base_dir, "blogs")
        self.image_dir = os.path.join(self.base_dir, "blog_images")
        for directory in [self.blog_dir, self.image_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
        
        # Initialize Stability AI client
        self.stability_api = client.StabilityInference(
            key=os.getenv('STABILITY_API_KEY'),
            verbose=True
        )

        # Define tech keyword mapping for better prompts
        self.tech_keywords = {
            # AI & ML
            'chatgpt': 'OpenAI ChatGPT interface, AI chat assistant, digital AI conversation',
            'gpt': 'GPT language model, OpenAI technology, neural network language model',
            'artificial intelligence': 'digital brain, neural networks visualization, AI processing',
            'machine learning': 'data pattern recognition, algorithm training, AI learning processes',
            'deep learning': 'neural networks architecture, deep neural networks, AI learning layers',
            
            # Software & Programming
            'python': 'Python programming language, code visualization, Python logo snake',
            'javascript': 'JavaScript code, web development, JS programming',
            'kubernetes': 'container orchestration, Kubernetes cluster visualization, K8s infrastructure',
            'docker': 'containerization, Docker containers, microservices architecture',
            
            # Hardware & Computing
            'cpu': 'computer processor chipset, semiconductor technology, processor architecture',
            'gpu': 'graphics processing unit, parallel computing, rendering hardware',
            'quantum computing': 'quantum bits visualization, quantum processor, quantum entanglement',
            
            # Companies & Products
            'apple': 'Apple technology ecosystem, Apple product design, Apple innovation',
            'microsoft': 'Microsoft technology, Windows interface, Azure cloud services',
            'google': 'Google search technology, Google AI development, Google digital services',
            'amazon': 'AWS cloud architecture, Amazon technology, Amazon web services',
            'tesla': 'Tesla autopilot visualization, Tesla AI systems, Tesla vehicle technology',
            'openai': 'OpenAI research visualization, GPT technology, AI text generation'
        }

    def generate_blog_images(self, blog_content, num_images=3):
        lines = blog_content.split('\n')
        title = lines[0].strip() if lines else "Blog Post"
        safe_title = re.sub(r'[^\w\-_\. ]', '', title[:30])
        prompts = self._create_prompts(blog_content, num_images)
        generated_images = []
        
        for i, prompt in enumerate(prompts):
            try:
                logger.info(f"Generated prompt {i+1}: {prompt}")
                # Generate image using Stability AI
                answers = self.stability_api.generate(
                    prompt=prompt,
                    seed=123,
                    steps=30,
                    cfg_scale=8.0,
                    width=512,
                    height=512,
                    samples=1
                )
                
                # Process and save the generated image
                for answer in answers:
                    img = Image.open(io.BytesIO(answer.artifacts[0].binary))
                    filename = os.path.join(self.image_dir, f"{safe_title}_image{i+1}.png")
                    img.save(filename)
                    generated_images.append(filename)
                    logger.info(f"Generated image saved as: {filename}")
                
                # Add small delay between generations
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error generating image {i+1}: {e}")
        
        return generated_images

    def _identify_tech_concepts(self, text):
        """Identify technology-related concepts in text to improve prompt relevance"""
        text_lower = text.lower()
        
        # Check for tech keywords
        matched_concepts = []
        for keyword, description in self.tech_keywords.items():
            if keyword in text_lower:
                matched_concepts.append((keyword, description))
        
        # If no specific tech matches, look for general tech terms
        general_tech_terms = ['technology', 'software', 'hardware', 'digital', 'algorithm', 'data']
        if not matched_concepts:
            for term in general_tech_terms:
                if term in text_lower:
                    matched_concepts.append((term, "digital technology visualization, advanced computing concept"))
        
        return matched_concepts

    def _create_prompts(self, blog_content, num_images):
        lines = blog_content.split('\n')
        title = lines[0].strip() if lines else "Blog Post"
        
        # Extract meaningful subheadings
        subheadings = [line.strip() for line in lines[1:100] if line and line.strip().startswith('##')]
        if not subheadings:
            subheadings = [line.strip() for line in lines[1:100] if line and not line.endswith('.') and len(line) < 100 and line != title]
        
        # Make sure we have enough content for prompts
        concepts = [title] + subheadings
        
        # Find tech concepts in the title and blog content for better prompts
        tech_concepts = self._identify_tech_concepts(title + ' ' + ' '.join(concepts[:5]))
        
        tech_specific_templates = [
            # Tech UI/Software templates
            "Realistic user interface of {subject}, detailed high-quality app interface design, high-end technology visualization",
            "Modern technology illustration of {subject}, detailed digital concept visualization, technological advancement",
            "Digital representation of {subject} technology, futuristic UI concept, detailed tech visualization",
            
            # Tech Hardware templates
            "Photorealistic hardware visualization of {subject}, detailed technology product rendering, cutting-edge device",
            "Technology infrastructure representing {subject}, data center perspective, enterprise technology architecture",
            
            # Tech Abstract templates
            "Abstract digital visualization of {subject}, high-tech concept art, futuristic technology illustration",
            "Advanced technology concept representing {subject}, digital innovation visualization, next-generation tech"
        ]
        
        standard_templates = [
            "Sophisticated digital visualization representing {subject}, clean modern aesthetic, professional infographic style",
            "Abstract technological concept art of {subject}, sleek futuristic design, innovative visualization",
            "Modern digital artwork showcasing {subject}, cutting-edge design, professional composition",
            "Strategic visual representation of {subject}, executive presentation quality, sophisticated layout"
        ]
        
        quality_modifiers = [
            ", photorealistic detail, volumetric lighting, ultra HD quality, 8K resolution",
            ", cinematic lighting, professional color grading, pristine clarity, studio quality",
            ", perfect composition, dramatic lighting, crystal clear details, magazine quality",
            ", award-winning photography style, professional post-processing, immaculate presentation"
        ]
        
        # Tech-specific style modifiers
        tech_style_modifiers = [
            ", resembling Apple keynote presentation style, premium tech product visualization",
            ", similar to Microsoft technical documentation imagery, enterprise technology visual",
            ", in the style of TechCrunch feature image, cutting-edge technology journalism visual",
            ", resembling IBM research visualization, enterprise-grade technical diagram style",
            ", similar to WIRED magazine technology feature illustration, modern tech journalism style"
        ]
        
        # For non-tech content, use these style modifiers
        general_style_modifiers = [
            ", corporate aesthetic, Bloomberg style visualization, executive presentation quality",
            ", Fortune 500 marketing material style, professional documentation grade",
            ", high-end business publication quality, Wall Street Journal infographic style",
            ", premium corporate branding aesthetic, Harvard Business Review style"
        ]
        
        negative_prompt = " --no text, no words, no letters, no numbers, no diagrams, no labels, no annotations"
        
        prompts = []
        for i in range(min(num_images, max(3, len(concepts)))):
            # Select the concept to visualize
            concept = concepts[i % len(concepts)]
            
            # Determine if we should use tech-specific templates
            templates = tech_specific_templates if tech_concepts else standard_templates
            style_modifiers = tech_style_modifiers if tech_concepts else general_style_modifiers
            
            # Use more specific tech terms if available
            subject_term = concept
            if tech_concepts:
                # For the first image, prioritize the main tech concept from the title
                if i == 0 and tech_concepts:
                    tech_keyword, tech_description = tech_concepts[0]
                    subject_term = f"{concept} - {tech_description}"
                # For other images, rotate through available tech concepts
                elif len(tech_concepts) > (i % len(tech_concepts)):
                    tech_keyword, tech_description = tech_concepts[i % len(tech_concepts)]
                    subject_term = f"{concept} - {tech_description}"
            
            # Build the prompt
            base_prompt = templates[i % len(templates)].format(subject=subject_term)
            quality = quality_modifiers[i % len(quality_modifiers)]
            style = style_modifiers[i % len(style_modifiers)]
            prompt = f"{base_prompt}{quality}{style}{negative_prompt}"
            prompts.append(prompt)
            
            # Log the prompt creation
            logger.info(f"Created prompt for concept '{concept}': {prompt[:100]}...")
            
        return prompts

def test_image_generator():
    try:
        print("Starting test...")
        generator = ImageGenerator()
        test_blog = '''ChatGPT 4.5: The Next Generation AI Assistant
        ## Advanced Natural Language Processing
        ChatGPT 4.5 introduces revolutionary improvements in understanding context and nuance.
        ## Multimodal Capabilities
        The new model can process and generate content across text, images, and code simultaneously.
        ## Technical Architecture
        Based on a trillion-parameter architecture with enhanced retrieval mechanisms.'''
        images = generator.generate_blog_images(test_blog, num_images=2)
        for image_path in images:
            if os.path.exists(image_path):
                print(f"✓ Successfully generated: {image_path}")
            else:
                print(f"✗ Failed to generate: {image_path}")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Script started")
    test_image_generator()
