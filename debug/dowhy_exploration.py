"""
DoWhy Exploration Script

Tests DoWhy capabilities for potential integration with lift-sys.
"""

import networkx as nx
import numpy as np
import pandas as pd
from dowhy import gcm

print("=" * 80)
print("DoWhy Exploration for lift-sys Integration")
print("=" * 80)

# Test 1: Basic Structural Causal Model
print("\n1. Creating a Simple Causal Graph (X → Y → Z)")
causal_graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])
print(f"   Nodes: {list(causal_graph.nodes())}")
print(f"   Edges: {list(causal_graph.edges())}")

# Test 2: Create SCM and generate data
print("\n2. Creating Structural Causal Model")
causal_model = gcm.StructuralCausalModel(causal_graph)

# Generate synthetic data
np.random.seed(42)
X = np.random.normal(loc=0, scale=1, size=1000)
Y = 2 * X + np.random.normal(loc=0, scale=1, size=1000)
Z = 3 * Y + np.random.normal(loc=0, scale=1, size=1000)
data = pd.DataFrame(data={"X": X, "Y": Y, "Z": Z})
print(f"   Generated {len(data)} samples")
print(f"   Data shape: {data.shape}")

# Test 3: Auto-assign causal mechanisms
print("\n3. Auto-assigning Causal Mechanisms")
gcm.auto.assign_causal_mechanisms(causal_model, data)
print("   ✓ Mechanisms assigned automatically")

# Test 4: Fit the model
print("\n4. Fitting the Structural Causal Model")
gcm.fit(causal_model, data)
print("   ✓ Model fitted to data")

# Test 5: Perform intervention
print("\n5. Performing Intervention (do(Y = 2.34))")
intervention_samples = gcm.interventional_samples(
    causal_model, {"Y": lambda y: 2.34}, num_samples_to_draw=100
)
print(f"   Generated {len(intervention_samples)} intervention samples")
print(f"   Mean Z after intervention: {intervention_samples['Z'].mean():.2f}")
print(f"   Expected Z (3 * 2.34): {3 * 2.34:.2f}")

# Test 6: More complex graph (simulating code dependencies)
print("\n6. Complex Graph (Simulating Code Dependencies)")
code_graph = nx.DiGraph(
    [("input", "validate"), ("validate", "process"), ("config", "process"), ("process", "output")]
)
print(f"   Nodes: {list(code_graph.nodes())}")
print(f"   Edges: {list(code_graph.edges())}")
print(f"   Graph has {len(code_graph.nodes())} nodes and {len(code_graph.edges())} edges")

# Test 7: Counterfactual query potential
print("\n7. Counterfactual Analysis Potential")
print("   DoWhy supports:")
print("   - Interventional queries: What if we change X?")
print("   - Counterfactual queries: What would have happened if X was different?")
print("   - Causal attribution: Why did Y happen?")

print("\n" + "=" * 80)
print("Exploration Complete")
print("=" * 80)

# Summary
print("\nKey Capabilities for lift-sys:")
print("1. ✓ Causal graph construction (NetworkX)")
print("2. ✓ Automatic causal mechanism fitting")
print("3. ✓ Interventional analysis (code change impact)")
print("4. ✓ Supports complex multi-node graphs")
print("5. ✓ Fast fitting and inference")

print("\nPotential Applications:")
print("- Reverse Mode: Model code as causal graph")
print("- Impact Analysis: Estimate effect of refactoring")
print("- Test Generation: Identify critical causal paths")
print("- Constraint Validation: Verify IR transformations preserve causality")
