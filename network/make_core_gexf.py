# this script file:
# 1) reads in the pajek file given as the first argument
# 2) calculates the (weighted) core number of each node, filters
# 3) finds the backbone of the network, filters
# 4) calculates statistics for the filtered network
# 5) saves the filtered network as a .gexf file

import csv
import networkx as nx
from networkx.algorithms.community.quality import modularity
from collections import defaultdict
from make_split_pajek import parse_pajek
from make_split_pajek import generate_pajek
import backboning
import traceback

def make_gexf(network_path,node_sort,nodes,edge_sort,edges,attributes=[]):
    # Load the full network
    with open(network_path+'.net','r') as network_pajek:
        G = parse_pajek(network_pajek)
    # Find partitions by attributes
    partition = {attr:defaultdict(lambda: set()) for attr in attributes}
    for node in G:
        for attr in attributes:
            partition[attr][G.nodes[node][attr]].add(node)
    # Now only for the subnetwork with known attributes
    attr_subgraph           = {}
    attr_subgraph_partition = {attr:defaultdict(lambda: set()) for attr in attributes}
    for attr in attributes:
        attr_nodes = [node for node in G.nodes() if G.nodes[node][attr] != "-" ]
        attr_subgraph[attr] = G.subgraph(attr_nodes)
        for node in attr_subgraph[attr]:
            attr_subgraph_partition[attr][attr_subgraph[attr].nodes[node][attr]].add(node)
    # Write basic stats to a text file
    stats_filename = network_path+"_"+node_sort+str(nodes)+".stats" if nodes else network_path+".stats"
    with open(stats_filename,"w") as stats_file:
        stats_file.write('# nodes\n')
        stats_file.write(str(G.number_of_nodes())+'\n')
        stats_file.write('# edges\n')
        stats_file.write(str(G.size())+'\n')
        stats_file.write('# total weight\n')
        stats_file.write(str(G.size(weight='weight'))+'\n')
        try:
            for attr in attributes:
                stats_file.write('# modularity '+attr+' \n')
                stats_file.write(str(modularity(G, partition[attr].values(), weight='weight'))+'\n')
            for attr in attributes:
                stats_file.write('# modularity '+attr+' - known only \n')
                stats_file.write(str(modularity(attr_subgraph[attr], attr_subgraph_partition[attr].values(), weight='weight'))+'\n')
        except:
            stats_file.write(traceback.format_exc())
    # Get the nodes in the core
    if nodes:
        core_nodes = sorted(G.nodes(), key=lambda n: float(G.node[n][node_sort]), reverse=True)[:nodes]
        G_core = G.subgraph(core_nodes)
    else:
        G_core = G
    # Write the nodes to a text file
    nodes_file = network_path+"_"+node_sort+str(nodes)+".nodes" if nodes else network_path+".nodes"
    with open(nodes_file,"w") as nodes_file:
        for node in G_core:
            meh = nodes_file.write(str(G.node[node].get('unique_id',node))+'\n')
    # Filter the edges
    if edge_sort:
        table, nnodes, nnedges = backboning.from_nx(G_core)
        nc_table = backboning.noise_corrected(table)
        if edges:
            G_filters = backboning.write_scores_nx(nc_table,edge_filter=(edge_sort,edges))
        else:
            G_filters = backboning.write_scores_nx(nc_table)
    else:
        G_filters = G_core
    # Put back any zero-degree nodes
    isolates = 0
    for node in G_core:
        if node not in G_filters:
            G_filters.add_node(node,**G_core.node[node])
            isolates += 1
    # Share node attributes
    for node in G_filters:
        for attr in G_core.node[node]:
            G_filters.node[node][attr] = G_core.node[node][attr]
    # Find partitions by attributes
    partition = {attr:defaultdict(lambda: set()) for attr in attributes}
    for node in G_core:
        for attr in attributes:
            partition[attr][G_core.nodes[node][attr]].add(node)
    # Now only for the subnetwork with known attributes
    attr_subgraph           = {}
    attr_subgraph_partition = {attr:defaultdict(lambda: set()) for attr in attributes}
    for attr in attributes:
        attr_nodes = [node for node in G_core.nodes() if G_core.nodes[node][attr] != "-" ]
        attr_subgraph[attr] = G_core.subgraph(attr_nodes)
        for node in attr_subgraph[attr]:
            attr_subgraph_partition[attr][attr_subgraph[attr].nodes[node][attr]].add(node)
    # Write filtered stats to a text file
    with open(stats_filename,"a") as stats_file:
        stats_file.write('# nodes - core\n')
        stats_file.write(str(G_core.number_of_nodes())+'\n')
        stats_file.write('# edges - core\n')
        stats_file.write(str(G_core.size())+'\n')
        stats_file.write('# total weight - core\n')
        stats_file.write(str(G_core.size(weight='weight'))+'\n')
        try:
            for attr in attributes:
                stats_file.write('# modularity '+attr+' - core\n')
                stats_file.write(str(modularity(G_core, partition[attr].values(), weight='weight'))+'\n')
            for attr in attributes:
                stats_file.write('# modularity '+attr+' - core known only \n')
                stats_file.write(str(modularity(attr_subgraph[attr], attr_subgraph_partition[attr].values(), weight='weight'))+'\n')
        except:
            stats_file.write(traceback.format_exc())
        stats_file.write('# edges - filtered core\n')
        stats_file.write(str(G_filters.size())+'\n')
        stats_file.write('# isolates - filtered core\n')
        stats_file.write(str(isolates)+'\n')
        stats_file.write('# total weight - filtered core\n')
        stats_file.write(str(G_filters.size(weight='weight'))+'\n')
    # Save as Gephi file
    gexf_file  = network_path+"_"+node_sort+str(nodes) if nodes else network_path
    gexf_file += "_"+edge_sort+str(int(100*edges))+".gexf" if edges else ".gexf"
    nx.write_gexf(G_filters, gexf_file)

if __name__ == '__main__':
    import argparse
    import os

    ################### ARGUMENTS #####################
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='The input network pajek file (.net, created by make_split_pajek.py)')
    parser.add_argument('--node_sort', default="core_number", help='The feature by which to choose the top nodes.')
    parser.add_argument('--nodes', type=int, default=None, help='The number of nodes to filter into the viz.')
    parser.add_argument('--edge_sort', default="noise_corrected_pct", help='The feature by which to choose the prominent edges.')
    parser.add_argument('--edges', type=float, default=None, help='The fraction of edges above which to filter into the viz.')
    #parser.add_argument('--raw', action="store_true", default=False, help='Give cutoffs in the raw values of the measures, instead.')
    parser.add_argument('--partition', action='append', default=[], help='Node attributes for which to calculate modularity.')

    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        raise OSError("Could not find the input file",args.input_file)
    ####################################################
    make_gexf(args.input_file.split(".net")[0],args.node_sort,args.nodes,args.edge_sort,args.edges,attributes=args.partition)
