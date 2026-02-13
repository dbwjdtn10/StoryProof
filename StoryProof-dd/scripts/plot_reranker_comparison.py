import matplotlib.pyplot as plt
import numpy as np

OUTPUT_IMAGE = "reranker_benchmark_result.png"

# Results from benchmark run
labels = ['Hybrid Search (Alpha=0.83)', 'Reranked (Cross-Encoder)']
accuracy = [0.3567, 0.4120]  # Hardcoded from previous run output
colors = ['#4e79a7', '#e15759']

def main():
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    bars = ax.bar(labels, accuracy, color=colors, width=0.5)
    
    # Add values on top
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.4f} ({height*100:.1f}%)',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
        
    # Add Improvement Arrow
    x0 = bars[0].get_x() + bars[0].get_width()/2
    y0 = bars[0].get_height()
    x1 = bars[1].get_x() + bars[1].get_width()/2
    y1 = bars[1].get_height()
    
    ax.annotate(f'+{(accuracy[1]-accuracy[0])*100:.2f}%p Improvement',
                xy=(x1, y1), xytext=(x0 + (x1-x0)/2, max(y0, y1) + 0.05),
                arrowprops=dict(arrowstyle='->', connectionstyle="arc3,rad=-0.2", color='black'),
                ha='center', fontsize=11, color='green', fontweight='bold')

    plt.ylim(0, 0.6)
    plt.ylabel('Top-5 Accuracy (Soft Match)')
    plt.title('Effect of Reranker on Retrieval Accuracy')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)
    print(f"Graph saved to {OUTPUT_IMAGE}")

if __name__ == "__main__":
    main()
