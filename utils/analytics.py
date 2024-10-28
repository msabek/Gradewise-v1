import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict
import streamlit as st

class AnalyticsDashboard:
    @staticmethod
    def create_grade_distribution_chart(assignments: List[Dict]):
        """Creates a histogram of grade distribution"""
        try:
            scores = [a.get('grade', {}).get('score', 0) for a in assignments]
            df = pd.DataFrame({'Score': scores})
            
            fig = px.histogram(
                df, 
                x='Score',
                nbins=10,
                title='Grade Distribution',
                labels={'Score': 'Grade', 'count': 'Number of Assignments'},
                template='plotly_white'
            )
            
            fig.update_layout(
                showlegend=False,
                xaxis_title="Grade",
                yaxis_title="Number of Assignments",
                height=400
            )
            return fig
        except Exception as e:
            st.error(f"Error creating grade distribution chart: {str(e)}")
            return None

    @staticmethod
    def create_success_rate_chart(assignments: List[Dict]):
        """Creates a pie chart showing success vs error rate"""
        try:
            status_counts = pd.DataFrame([{'Status': a.get('status', 'unknown')} for a in assignments])['Status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Processing Success Rate',
                template='plotly_white',
                color_discrete_map={'success': 'green', 'error': 'red', 'unknown': 'gray'}
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            st.error(f"Error creating success rate chart: {str(e)}")
            return None

    @staticmethod
    def calculate_statistics(assignments: List[Dict]) -> Dict:
        """Calculates key statistics from assignments"""
        try:
            scores = [a.get('grade', {}).get('score', 0) for a in assignments]
            stats = {
                'Total Assignments': len(assignments),
                'Average Score': sum(scores) / len(scores) if scores else 0,
                'Highest Score': max(scores) if scores else 0,
                'Lowest Score': min(scores) if scores else 0,
                'Success Rate': sum(1 for a in assignments if a.get('status') == 'success') / len(assignments) * 100 if assignments else 0
            }
            return stats
        except Exception as e:
            st.error(f"Error calculating statistics: {str(e)}")
            return {
                'Total Assignments': 0,
                'Average Score': 0,
                'Highest Score': 0,
                'Lowest Score': 0,
                'Success Rate': 0
            }

    @staticmethod
    def create_performance_comparison(assignments: List[Dict]):
        """Creates a bar chart comparing individual assignment scores"""
        try:
            df = pd.DataFrame([{
                'Assignment': a.get('filename', f'Assignment {i+1}'),
                'Score': a.get('grade', {}).get('score', 0)
            } for i, a in enumerate(assignments)])
            
            fig = px.bar(
                df,
                x='Assignment',
                y='Score',
                title='Assignment Score Comparison',
                template='plotly_white',
                color='Score',
                color_continuous_scale='RdYlGn'
            )
            
            fig.update_xaxes(tickangle=45)
            fig.update_layout(
                xaxis_title="Assignment Name",
                yaxis_title="Score",
                showlegend=False,
                height=500
            )
            return fig
        except Exception as e:
            st.error(f"Error creating performance comparison chart: {str(e)}")
            return None

    @staticmethod
    def display_dashboard(assignments: List[Dict]):
        """Displays the complete analytics dashboard"""
        try:
            if not assignments:
                st.info("No grading data available for analysis. Please process some assignments first.")
                return

            # Key Statistics
            st.subheader("📈 Key Statistics")
            stats = AnalyticsDashboard.calculate_statistics(assignments)
            
            # Use columns for better layout
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total Assignments",
                    f"{stats['Total Assignments']}",
                    delta=None,
                    help="Total number of assignments processed"
                )
                st.metric(
                    "Success Rate",
                    f"{stats['Success Rate']:.1f}%",
                    delta=None,
                    help="Percentage of assignments processed successfully"
                )
            
            with col2:
                st.metric(
                    "Average Score",
                    f"{stats['Average Score']:.2f}",
                    delta=None,
                    help="Average score across all assignments"
                )
                st.metric(
                    "Highest Score",
                    f"{stats['Highest Score']:.2f}",
                    delta=None,
                    help="Highest score achieved"
                )
            
            with col3:
                st.metric(
                    "Lowest Score",
                    f"{stats['Lowest Score']:.2f}",
                    delta=None,
                    help="Lowest score received"
                )
            
            st.markdown("---")

            # Visualizations in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                grade_dist = AnalyticsDashboard.create_grade_distribution_chart(assignments)
                if grade_dist:
                    st.plotly_chart(grade_dist, use_container_width=True)

            with col2:
                success_rate = AnalyticsDashboard.create_success_rate_chart(assignments)
                if success_rate:
                    st.plotly_chart(success_rate, use_container_width=True)

            st.markdown("---")

            # Performance Comparison (full width)
            performance_comp = AnalyticsDashboard.create_performance_comparison(assignments)
            if performance_comp:
                st.plotly_chart(performance_comp, use_container_width=True)

            st.markdown("---")

            # Detailed Analysis Table
            st.subheader("📋 Detailed Analysis")
            try:
                analysis_df = pd.DataFrame([{
                    'Assignment': a.get('filename', f'Assignment {i+1}'),
                    'Score': a.get('grade', {}).get('score', 0),
                    'Status': a.get('status', 'unknown'),
                    'Feedback': a.get('grade', {}).get('feedback', '')[:100] + '...' 
                        if len(a.get('grade', {}).get('feedback', '')) > 100 
                        else a.get('grade', {}).get('feedback', '')
                } for i, a in enumerate(assignments)])
                
                st.dataframe(
                    analysis_df.style
                    .highlight_max(subset=['Score'], color='lightgreen')
                    .highlight_min(subset=['Score'], color='lightpink')
                    .format({'Score': '{:.2f}'}),
                    use_container_width=True,
                    height=400
                )
            except Exception as e:
                st.error(f"Error displaying analysis table: {str(e)}")

        except Exception as e:
            st.error(f"Error displaying dashboard: {str(e)}")
