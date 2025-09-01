#!/usr/bin/env python3
"""
Lead clustering system for grouping similar prospects by characteristics and themes
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# ML imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import regex as re

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClusterResult:
    """Represents a clustering result"""
    cluster_id: int
    cluster_label: str
    companies: List[str]
    avg_score: float
    common_themes: List[str]
    characteristics: Dict[str, Any]
    size: int
    created_at: str

class TextProcessor:
    """Handles text preprocessing for clustering"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        # Add business-specific stop words
        self.stop_words.update([
            'company', 'business', 'organization', 'team', 'people', 
            'work', 'working', 'use', 'using', 'get', 'need', 'want'
        ])
    
    def clean_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []
        
        # Clean text
        clean = self.clean_text(text)
        
        # Tokenize and lemmatize
        tokens = nltk.word_tokenize(clean)
        keywords = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]
        
        return keywords

class LeadClusterer:
    """Main clustering system for leads"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.text_processor = TextProcessor()
        self.clusters = {}
        self.feature_names = []
        
    def extract_features(self, leads_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Extract features from lead data for clustering"""
        features = []
        
        for lead in leads_data:
            company = lead.get('company', '')
            score = lead.get('score', 0)
            
            # Text features
            justification = lead.get('justification', '')
            summary = ' '.join(lead.get('summary', []))
            
            # Combine text for analysis
            combined_text = f"{justification} {summary}"
            
            # Breakdown features (if available)
            breakdown = lead.get('breakdown', {})
            
            feature_dict = {
                'company': company,
                'score': score,
                'text_content': combined_text,
                'text_length': len(combined_text),
                'justification_length': len(justification)
            }
            
            # Add breakdown dimensions
            for dim, value in breakdown.items():
                if isinstance(value, (int, float)):
                    feature_dict[f'breakdown_{dim}'] = value
            
            # Extract priority as numeric
            priority = lead.get('priority', 'Medium')
            priority_map = {'High': 3, 'Medium': 2, 'Low': 1}
            feature_dict['priority_numeric'] = priority_map.get(priority, 2)
            
            features.append(feature_dict)
        
        return pd.DataFrame(features)
    
    def prepare_clustering_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """Prepare features for clustering algorithms"""
        # Text vectorization
        text_vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        text_features = text_vectorizer.fit_transform(df['text_content']).toarray()
        text_feature_names = [f"text_{name}" for name in text_vectorizer.get_feature_names_out()]
        
        # Numerical features
        numeric_cols = [col for col in df.columns if col not in ['company', 'text_content'] and df[col].dtype in [int, float]]
        numeric_features = df[numeric_cols].fillna(0).values
        
        # Combine features
        all_features = np.hstack([text_features, numeric_features])
        all_feature_names = text_feature_names + numeric_cols
        
        # Scale features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(all_features)
        
        self.feature_names = all_feature_names
        
        return scaled_features, all_feature_names
    
    def find_optimal_clusters(self, features: np.ndarray, max_clusters: int = 8) -> int:
        """Find optimal number of clusters using silhouette score"""
        if len(features) < 4:
            return min(2, len(features))
        
        best_score = -1
        best_k = 2
        
        for k in range(2, min(max_clusters + 1, len(features))):
            try:
                kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                labels = kmeans.fit_predict(features)
                
                if len(set(labels)) > 1:  # Ensure we have multiple clusters
                    score = silhouette_score(features, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
            except Exception as e:
                logger.warning(f"Error with k={k}: {e}")
                continue
        
        return best_k
    
    def cluster_leads(self, leads_data: List[Dict[str, Any]], method: str = 'kmeans', n_clusters: Optional[int] = None) -> Dict[int, ClusterResult]:
        """Cluster leads and return cluster results"""
        
        if len(leads_data) < 2:
            logger.warning("Not enough leads for clustering")
            return {}
        
        logger.info(f"Clustering {len(leads_data)} leads using {method}")
        
        # Extract and prepare features
        df = self.extract_features(leads_data)
        features, feature_names = self.prepare_clustering_features(df)
        
        # Determine number of clusters
        if n_clusters is None:
            n_clusters = self.find_optimal_clusters(features)
        
        logger.info(f"Using {n_clusters} clusters")
        
        # Perform clustering
        if method == 'kmeans':
            clusterer = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
        elif method == 'hierarchical':
            clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        elif method == 'dbscan':
            clusterer = DBSCAN(eps=0.5, min_samples=2)
        else:
            raise ValueError(f"Unknown clustering method: {method}")
        
        # Fit clustering
        cluster_labels = clusterer.fit_predict(features)
        
        # Analyze clusters
        clusters = self._analyze_clusters(df, cluster_labels, leads_data)
        
        self.clusters = clusters
        return clusters
    
    def _analyze_clusters(self, df: pd.DataFrame, labels: np.ndarray, original_data: List[Dict]) -> Dict[int, ClusterResult]:
        """Analyze clustering results and extract insights"""
        clusters = {}
        unique_labels = set(labels)
        
        for cluster_id in unique_labels:
            if cluster_id == -1:  # DBSCAN noise
                continue
                
            # Get cluster members
            cluster_mask = labels == cluster_id
            cluster_df = df[cluster_mask]
            cluster_data = [original_data[i] for i in range(len(original_data)) if cluster_mask[i]]
            
            # Basic statistics
            companies = cluster_df['company'].tolist()
            scores = cluster_df['score'].tolist()
            avg_score = np.mean(scores) if scores else 0
            
            # Extract common themes from text
            all_text = ' '.join(cluster_df['text_content'].tolist())
            common_themes = self._extract_themes(all_text)
            
            # Analyze characteristics
            characteristics = self._analyze_cluster_characteristics(cluster_df, cluster_data)
            
            # Generate cluster label
            cluster_label = self._generate_cluster_label(characteristics, common_themes, avg_score)
            
            clusters[cluster_id] = ClusterResult(
                cluster_id=cluster_id,
                cluster_label=cluster_label,
                companies=companies,
                avg_score=avg_score,
                common_themes=common_themes,
                characteristics=characteristics,
                size=len(companies),
                created_at=datetime.now().isoformat()
            )
        
        return clusters
    
    def _extract_themes(self, text: str, top_n: int = 5) -> List[str]:
        """Extract top themes from cluster text"""
        if not text.strip():
            return []
        
        try:
            # Use TF-IDF to find important terms
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Get top scoring terms
            top_indices = np.argsort(tfidf_scores)[-top_n:][::-1]
            themes = [feature_names[i] for i in top_indices if tfidf_scores[i] > 0]
            
            return themes
        except Exception as e:
            logger.warning(f"Error extracting themes: {e}")
            return []
    
    def _analyze_cluster_characteristics(self, cluster_df: pd.DataFrame, cluster_data: List[Dict]) -> Dict[str, Any]:
        """Analyze characteristics of a cluster"""
        characteristics = {}
        
        # Score statistics
        scores = cluster_df['score'].tolist()
        if scores:
            characteristics['score_stats'] = {
                'mean': float(np.mean(scores)),
                'std': float(np.std(scores)),
                'min': float(np.min(scores)),
                'max': float(np.max(scores))
            }
        
        # Priority distribution
        priorities = [item.get('priority', 'Medium') for item in cluster_data]
        priority_counts = pd.Series(priorities).value_counts().to_dict()
        characteristics['priority_distribution'] = priority_counts
        
        # Breakdown analysis (if available)
        breakdown_dims = ['industry_fit', 'scale_indicators', 'platform_maturity', 
                         'growth_churn_challenges', 'revenue_sophistication']
        
        breakdown_stats = {}
        for dim in breakdown_dims:
            values = []
            for item in cluster_data:
                breakdown = item.get('breakdown', {})
                if dim in breakdown and isinstance(breakdown[dim], (int, float)):
                    values.append(breakdown[dim])
            
            if values:
                breakdown_stats[dim] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values))
                }
        
        if breakdown_stats:
            characteristics['breakdown_stats'] = breakdown_stats
        
        # Text characteristics
        text_lengths = cluster_df['text_length'].tolist()
        if text_lengths:
            characteristics['text_stats'] = {
                'avg_length': float(np.mean(text_lengths)),
                'total_companies': len(cluster_df)
            }
        
        return characteristics
    
    def _generate_cluster_label(self, characteristics: Dict, themes: List[str], avg_score: float) -> str:
        """Generate a descriptive label for the cluster"""
        # Score-based prefix
        if avg_score >= 80:
            score_label = "High-Value"
        elif avg_score >= 60:
            score_label = "Medium-Value"
        else:
            score_label = "Low-Value"
        
        # Theme-based description
        if themes:
            # Look for key business themes
            business_themes = []
            for theme in themes[:3]:
                if any(word in theme.lower() for word in ['growth', 'scale', 'expand']):
                    business_themes.append("Growth-Stage")
                elif any(word in theme.lower() for word in ['billing', 'payment', 'subscription']):
                    business_themes.append("Billing-Focused")
                elif any(word in theme.lower() for word in ['tech', 'engineering', 'platform']):
                    business_themes.append("Tech-Forward")
                elif any(word in theme.lower() for word in ['enterprise', 'large', 'big']):
                    business_themes.append("Enterprise")
                elif any(word in theme.lower() for word in ['startup', 'early', 'small']):
                    business_themes.append("Early-Stage")
            
            if business_themes:
                theme_label = business_themes[0]
            else:
                # Use first theme as fallback
                theme_label = themes[0].title().replace('_', ' ')
        else:
            theme_label = "General"
        
        return f"{score_label} {theme_label} Prospects"
    
    def get_cluster_insights(self, cluster_id: int) -> Dict[str, Any]:
        """Get detailed insights for a specific cluster"""
        if cluster_id not in self.clusters:
            return {"error": "Cluster not found"}
        
        cluster = self.clusters[cluster_id]
        
        insights = {
            "cluster_info": asdict(cluster),
            "recommendations": self._generate_recommendations(cluster),
            "next_steps": self._suggest_next_steps(cluster)
        }
        
        return insights
    
    def _generate_recommendations(self, cluster: ClusterResult) -> List[str]:
        """Generate actionable recommendations for a cluster"""
        recommendations = []
        
        # Score-based recommendations
        if cluster.avg_score >= 80:
            recommendations.append("Priority outreach - high conversion potential")
            recommendations.append("Consider personalized demo or consultation")
        elif cluster.avg_score >= 60:
            recommendations.append("Nurture with targeted content")
            recommendations.append("Follow up with case studies")
        else:
            recommendations.append("Long-term nurturing approach")
            recommendations.append("Educational content to build awareness")
        
        # Size-based recommendations
        if cluster.size >= 5:
            recommendations.append("Create cluster-specific email campaign")
            recommendations.append("Develop targeted messaging for this segment")
        
        # Theme-based recommendations
        for theme in cluster.common_themes[:2]:
            if 'growth' in theme.lower():
                recommendations.append("Emphasize scalability benefits")
            elif 'billing' in theme.lower():
                recommendations.append("Focus on billing efficiency gains")
            elif 'tech' in theme.lower():
                recommendations.append("Highlight technical integration capabilities")
        
        return recommendations
    
    def _suggest_next_steps(self, cluster: ClusterResult) -> List[str]:
        """Suggest immediate next steps for a cluster"""
        steps = []
        
        if cluster.size <= 3:
            steps.append("Research individual companies for personalized outreach")
        else:
            steps.append("Create bulk outreach sequence for cluster")
        
        steps.append(f"Prepare talking points around: {', '.join(cluster.common_themes[:3])}")
        steps.append("Assign to appropriate sales rep based on cluster characteristics")
        
        return steps
    
    def export_clusters(self, output_path: str):
        """Export cluster results to JSON"""
        export_data = {}
        for cluster_id, cluster in self.clusters.items():
            export_data[cluster_id] = asdict(cluster)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported clusters to {output_path}")
    
    def print_cluster_summary(self):
        """Print a summary of all clusters"""
        if not self.clusters:
            print("No clusters available")
            return
        
        print(f"\n🎯 Lead Clustering Summary")
        print("=" * 50)
        print(f"Total Clusters: {len(self.clusters)}")
        
        # Sort clusters by average score
        sorted_clusters = sorted(self.clusters.values(), key=lambda x: x.avg_score, reverse=True)
        
        for cluster in sorted_clusters:
            print(f"\n📊 {cluster.cluster_label}")
            print(f"   Companies: {cluster.size} | Avg Score: {cluster.avg_score:.1f}")
            print(f"   Companies: {', '.join(cluster.companies[:3])}{'...' if cluster.size > 3 else ''}")
            print(f"   Themes: {', '.join(cluster.common_themes[:3])}")
            
            if cluster.characteristics.get('priority_distribution'):
                priorities = cluster.characteristics['priority_distribution']
                print(f"   Priorities: {priorities}")

# Example usage and testing
def demo_clustering():
    """Demonstrate lead clustering with sample data"""
    # Sample lead data
    sample_leads = [
        {
            "company": "Shopify",
            "score": 75,
            "priority": "High",
            "justification": "Strong subscription billing needs with international expansion",
            "summary": ["Growing SaaS platform", "Complex billing requirements", "Enterprise scale"],
            "breakdown": {"industry_fit": 18, "scale_indicators": 15, "platform_maturity": 12}
        },
        {
            "company": "Netflix",
            "score": 85,
            "priority": "High", 
            "justification": "Large subscription base with churn management focus",
            "summary": ["Media streaming leader", "Retention optimization", "Global billing complexity"],
            "breakdown": {"industry_fit": 20, "scale_indicators": 17, "platform_maturity": 16}
        },
        {
            "company": "Zoom",
            "score": 80,
            "priority": "High",
            "justification": "Rapid growth requiring better billing infrastructure",
            "summary": ["Video conferencing growth", "Scaling billing systems", "Enterprise expansion"],
            "breakdown": {"industry_fit": 16, "scale_indicators": 18, "platform_maturity": 14}
        },
        {
            "company": "Notion",
            "score": 65,
            "priority": "Medium",
            "justification": "Early stage but showing subscription growth potential", 
            "summary": ["Productivity software", "Growing user base", "Simple billing currently"],
            "breakdown": {"industry_fit": 15, "scale_indicators": 10, "platform_maturity": 10}
        },
        {
            "company": "Figma",
            "score": 70,
            "priority": "Medium",
            "justification": "Design tool with team subscriptions, moderate complexity",
            "summary": ["Design platform growth", "Team billing features", "API integrations"],
            "breakdown": {"industry_fit": 16, "scale_indicators": 12, "platform_maturity": 14}
        }
    ]
    
    # Initialize clusterer
    clusterer = LeadClusterer()
    
    # Perform clustering
    clusters = clusterer.cluster_leads(sample_leads, method='kmeans')
    
    # Print results
    clusterer.print_cluster_summary()
    
    # Show detailed insights for each cluster
    for cluster_id in clusters:
        insights = clusterer.get_cluster_insights(cluster_id)
        print(f"\n🔍 Detailed Insights for Cluster {cluster_id}:")
        print(f"Recommendations: {insights['recommendations'][:2]}")
        print(f"Next Steps: {insights['next_steps'][:2]}")
    
    return clusterer

if __name__ == "__main__":
    demo_clustering()
