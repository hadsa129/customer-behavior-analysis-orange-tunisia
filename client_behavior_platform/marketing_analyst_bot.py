import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import re
import ast
import traceback
from datetime import datetime
import ollama

class MarketingAnalystBot:
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the Marketing Analyst Bot with data directory and models.
        
        Args:
            data_dir (str): Directory containing all CSV files
        """
        self.data_dir = data_dir
        self.analyzer_model = "qwen2.5:3b"
        self.coder_model = "qwen2.5-coder:1.5b"
        self.system_prompt = self._create_system_prompt()
        self.df_cache = {}
        self.load_all_data()
    
    def _create_system_prompt(self) -> str:
        """Create an enriched system prompt with all necessary context."""
        return """
        You are an expert Marketing Data Analyst at Orange with deep knowledge of customer behavior analysis.
        Your role is to help marketing agents understand customer behavior patterns using available data.
        
        DATASET OVERVIEW:
        - Client Information: Monthly snapshots of client behavior and preferences
        - Purchases: Detailed records of all purchases
        - Recharges: Records of all recharges made by clients
        - Consumption: Monthly data, voice, and SMS usage
        - Churn Data: Information about customer churn
        
        KEY BUSINESS CONCEPTS:
        - MSISDN: Unique identifier for each customer's SIM card
        - Engagement Score: Metric indicating how engaged a customer is (0-100)
        - Rentability: Whether a customer is profitable (actif) or not (passif)
        - Segments: Various customer segments based on behavior and preferences
        
        When analyzing data, always consider:
        1. Customer lifetime value
        2. Engagement patterns
        3. Purchase behavior
        4. Usage patterns
        5. Churn risk
        
        Provide clear, actionable insights with relevant metrics and visualizations when appropriate.
        """
    
    def load_all_data(self):
        """Load all CSV files into memory."""
        try:
            # Load client info files
            client_info_files = [f for f in os.listdir(self.data_dir) if 'df_client_info' in f]
            self.client_info_dfs = {}
            for file in client_info_files:
                month_year = file.split('_')[-1].replace('.csv', '')
                self.client_info_dfs[month_year] = pd.read_csv(os.path.join(self.data_dir, file))
            
            # Load purchase data
            purchase_files = [f for f in os.listdir(self.data_dir) if 'achat_' in f]
            self.purchase_dfs = {}
            for file in purchase_files:
                month_year = file.split('_')[-1].replace('.csv', '')
                self.purchase_dfs[month_year] = pd.read_csv(os.path.join(self.data_dir, file))
            
            # Load recharge data
            recharge_files = [f for f in os.listdir(self.data_dir) if 'recharge_' in f]
            self.recharge_dfs = {}
            for file in recharge_files:
                month_year = file.split('_')[-1].replace('.csv', '')
                self.recharge_dfs[month_year] = pd.read_csv(os.path.join(self.data_dir, file))
            
            # Load consumption data
            consumption_files = [f for f in os.listdir(self.data_dir) if 'consommation_mois_' in f]
            self.consumption_dfs = {}
            for file in consumption_files:
                month_year = file.split('_')[-1].replace('.csv', '')
                self.consumption_dfs[month_year] = pd.read_csv(os.path.join(self.data_dir, file))
            
            # Load segmentation data
            segmentation_files = [f for f in os.listdir(self.data_dir) if 'segmentation_mois_' in f]
            self.segmentation_dfs = {}
            for file in segmentation_files:
                month_year = file.split('_')[-1].replace('.csv', '')
                self.segmentation_dfs[month_year] = pd.read_csv(os.path.join(self.data_dir, file))
            
            # Load churn data
            self.churn_df = pd.read_csv(os.path.join(self.data_dir, 'churn_par_client_par_mois.csv'))
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise
    
    def analyze_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine intent and required data.
        
        Args:
            user_query (str): The user's natural language query
            
        Returns:
            Dict containing analysis of the query
        """
        prompt = f"""
        Analyze the following marketing query and determine:
        1. The main intent (e.g., segment analysis, trend analysis, customer profiling)
        2. Required time periods
        3. Key metrics to analyze
        4. Relevant customer segments
        5. Any specific filters or conditions
        
        Query: {user_query}
        
        Respond in JSON format with these keys:
        {{
            "intent": "description of the main intent",
            "time_periods": ["list", "of", "relevant", "periods"],
            "metrics": ["list", "of", "metrics"],
            "segments": ["list", "of", "relevant", "segments"],
            "filters": ["list", "of", "filter", "conditions"]
        }}
        """
        
        try:
            response = ollama.chat(
                model=self.analyzer_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the JSON response
            analysis = json.loads(response['message']['content'])
            return analysis
            
        except Exception as e:
            print(f"Error in analyze_intent: {str(e)}")
            return {
                "intent": "unknown",
                "time_periods": [],
                "metrics": [],
                "segments": [],
                "filters": []
            }
    
    def generate_analysis_code(self, analysis: Dict[str, Any]) -> str:
        """
        Generate Python code for data analysis based on the query analysis.
        
        Args:
            analysis (Dict): The analysis of the user query
            
        Returns:
            str: Python code for data analysis
        """
        prompt = f"""
        Based on the following analysis of a marketing query, generate Python code to perform the analysis.
        
        Analysis: {json.dumps(analysis, indent=2)}
        
        Available data:
        - Client Info: self.client_info_dfs[month_year]
        - Purchases: self.purchase_dfs[month_year]
        - Recharges: self.recharge_dfs[month_year]
        - Consumption: self.consumption_dfs[month_year]
        - Segmentation: self.segmentation_dfs[month_year]
        - Churn: self.churn_df
        
        The code should:
        1. Load the required data
        2. Perform necessary transformations and filtering
        3. Calculate requested metrics
        4. Return results in a clear format
        
        Return ONLY the Python code, properly formatted and ready to execute.
        """
        
        try:
            response = ollama.chat(
                model=self.coder_model,
                messages=[
                    {"role": "system", "content": "You are a Python data analysis expert. Generate efficient, well-commented code."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error in generate_analysis_code: {str(e)}")
            return ""
    
    def execute_analysis_code(self, code: str) -> Any:
        """
        Execute the generated analysis code in a controlled environment.
        
        Args:
            code (str): The Python code to execute
            
        Returns:
            The result of the code execution
        """
        try:
            # Create a safe execution environment
            local_vars = {
                'pd': pd,
                'np': np,
                'self': self
            }
            
            # Execute the code
            exec(code, globals(), local_vars)
            
            # Return the result if it exists
            if 'result' in local_vars:
                return local_vars['result']
            return None
            
        except Exception as e:
            print(f"Error executing analysis code: {str(e)}")
            return None
    
    def reformat_results(self, analysis: Dict[str, Any], results: Any) -> str:
        """
        Reformat the analysis results into a human-readable format.
        
        Args:
            analysis (Dict): The original query analysis
            results (Any): The analysis results
            
        Returns:
            str: Human-readable analysis results
        """
        prompt = f"""
        You are a marketing data analyst at Orange. 
        
        Original Query Analysis:
        {json.dumps(analysis, indent=2)}
        
        Analysis Results:
        {str(results)[:2000]}...  # Truncate very long results
        
        Please provide a clear, concise, and insightful explanation of these results for a marketing professional.
        Include key takeaways, any surprising findings, and potential next steps or recommendations.
        """
        
        try:
            response = ollama.chat(
                model=self.analyzer_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error in reformat_results: {str(e)}")
            return "An error occurred while processing the results."
    
    def process_query(self, user_query: str) -> str:
        """
        Process a user query end-to-end.
        
        Args:
            user_query (str): The user's natural language query
            
        Returns:
            str: The analysis results in a human-readable format
        """
        try:
            # Step 1: Analyze the query
            analysis = self.analyze_intent(user_query)
            
            # Step 2: Generate analysis code
            code = self.generate_analysis_code(analysis)
            
            # Step 3: Execute the code
            results = self.execute_analysis_code(code)
            
            # Step 4: Reformat results
            response = self.reformat_results(analysis, results)
            
            return response
            
        except Exception as e:
            error_msg = f"An error occurred while processing your query: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return error_msg

# Example usage
if __name__ == "__main__":
    # Initialize the bot with the path to your data directory
    bot = MarketingAnalystBot(data_dir="path/to/your/data/directory")
    
    # Example query
    query = "Show me the top 5 most engaged customers in February 2025"
    
    # Get and print the analysis
    result = bot.process_query(query)
    print("\nAnalysis Results:")
    print("-" * 80)
    print(result)
