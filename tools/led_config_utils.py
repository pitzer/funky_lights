import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from numpy import unique
from numpy import where
import math


class Node:
    def __init__(self, p):
        self.p = p
        self.next = None

    def distance(self, other_node):
        return np.linalg.norm(self.p - other_node.p)


def pca(data):
    # Calculate the mean of the points, i.e. the 'center' of the cloud
    datamean = data.mean(axis=0)
    # print('mean ' + str(datamean))

    # PCA to generate a line representation for each tube
    mu = data.mean(0)
    C = np.cov(data - mu, rowvar=False)
    d, u = np.linalg.eigh(C)
    U = u.T[::-1]

    # Project points onto the principle axes
    Z = np.dot(data - mu, U.T)
    # print('min Z ' + str(Z.min()))
    # print('max Z ' + str(Z.max()))

    return Z, U, mu


def cluster(data, eps, min_samples):
    model = DBSCAN(eps=eps, min_samples=min_samples)

    # fit model and predict clusters
    labels = model.fit_predict(data)

    # retrieve unique clusters
    clusters = unique(labels)

    if False:
        x2 = Z.T[0]
        y2 = Z.T[1]

        # create scatter plot for samples from each cluster
        for cluster in clusters:
            # get row indexes for samples with this cluster
            row_ix = where(labels == cluster)
            # create scatter of these samples
            plt.scatter(x2[row_ix], y2[row_ix], s=3)
        # show the plot
        plt.rcParams['figure.figsize'] = [25, 5]
        plt.axis('scaled')
        plt.show()
    
    return clusters, labels


def create_line_segments(data, clusters, labels):
    # First create an unordered list of nodes, one per cluster with using the mean of the cluster points.
    nodes = []
    for cluster in clusters:
        if cluster < 0: 
            continue
        row_ix = where(labels == cluster)
        cluster_points = data[row_ix]
        node = Node(p=cluster_points.mean(axis=0))
        nodes.append(node)
    if len(nodes) == 0: 
        return None

    # Connect nodes to line segments starting from a random node and extending in both directions the result is a start and an end node connected in a linked list
    start = nodes.pop()
    end = start
    while len(nodes) > 0:
        min_node = None
        min_dist = float('inf')
        closest_to_start = True

        for node in nodes:
            start_dist = start.distance(node)
            end_dist = end.distance(node)

            if start_dist < min_dist and start_dist <= end_dist:
                min_dist = start_dist
                min_node = node
                closest_to_start = True

            if end_dist < min_dist and end_dist < start_dist:
                min_dist = end_dist
                min_node = node
                closest_to_start = False

        if closest_to_start:
            min_node.next = start
            start = min_node
        else:
            end.next = min_node
            end = min_node

        nodes.remove(min_node)

    return start


def line_segments_length(start):
    n = start
    total_length = 0
    while True:
        if n.next == None:
            break
        total_length = total_length + n.distance(n.next)
        n = n.next
    return total_length


# Generate LED positions by tracing along the line segments until the correct number of LED are created
def trace_line_segments(start, num_leds, offset, led_dist):
    segment_points = []
    fraction = 0
    n = start
    dist = offset
    for i in range(num_leds):
        new_fraction = fraction + dist / n.distance(n.next)
        while new_fraction >= 1:
            # Move to next segment
            dist = dist - (1 - fraction) * n.distance(n.next)
            n = n.next
            fraction = 0
            new_fraction = dist / n.distance(n.next)

        fraction = new_fraction
        p = n.p + fraction * (n.next.p - n.p)
        segment_points.append(p)
        dist = led_dist

    return np.array(segment_points)


def generate_led_positions(data, clusters, labels, start_offset, end_offset, leds_per_meter):
    leds_distance = 1 / leds_per_meter
    segments = create_line_segments(data, clusters, labels)
    if segments == None:
        return [], 0
    length = line_segments_length(segments)
    length = length - start_offset - end_offset
    num_leds = math.floor(length * leds_per_meter)
    points = trace_line_segments(segments, num_leds, start_offset, leds_distance)
    return points, length


def prepare_data(group):
    x = np.array([v[0] for v in group.vertices])
    y = np.array([v[1] for v in group.vertices])
    z = np.array([v[2] for v in group.vertices])

    data = np.concatenate((x[:, np.newaxis],
                        y[:, np.newaxis],
                        z[:, np.newaxis]),
                        axis=1)
    return data


def plot_segment(data, clusters, labels, segment_points):
    Z, U, mu = pca(data)
    x2 = Z.T[0]
    y2 = Z.T[1]

    # create scatter plot for samples from each cluster
    for cluster in clusters:
        # get row indexes for samples with this cluster
        row_ix = where(labels == cluster)
        # create scatter of these samples
        plt.scatter(x2[row_ix], y2[row_ix], s=3)

    # # create scatter plot for line segments
    # print('U ' + str(U))
    L = np.dot(segment_points - mu, U.T)
    xl2 = L.T[0]
    yl2 = L.T[1]
    plt.scatter(xl2, yl2, s=3)

    plt.axis('scaled')
    plt.show()
    plt.rcParams['figure.figsize'] = [25, 5]


def project_2d(data):
    Z, U, mu = pca(data)
    return np.dot(data - mu, U.T)[:,:2]