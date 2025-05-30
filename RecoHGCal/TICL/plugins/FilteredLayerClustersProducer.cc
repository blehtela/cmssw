// Author: Felice Pantaleo, Marco Rovere - felice.pantaleo@cern.ch, marco.rovere@cern.ch
// Date: 09/2018

// user include files
#include "FWCore/Framework/interface/ESHandle.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/ESGetToken.h"

#include "DataFormats/ParticleFlowReco/interface/PFCluster.h"
#include "RecoLocalCalo/HGCalRecAlgos/interface/RecHitTools.h"

#include "ClusterFilterFactory.h"
#include "ClusterFilterBase.h"

#include <string>

class FilteredLayerClustersProducer : public edm::stream::EDProducer<> {
public:
  FilteredLayerClustersProducer(const edm::ParameterSet&);
  ~FilteredLayerClustersProducer() override {}
  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);
  void beginRun(edm::Run const&, edm::EventSetup const&) override;
  void produce(edm::Event&, const edm::EventSetup&) override;

private:
  edm::EDGetTokenT<std::vector<reco::CaloCluster>> clusters_token_;
  edm::EDGetTokenT<std::vector<float>> clustersMask_token_;
  edm::ESGetToken<CaloGeometry, CaloGeometryRecord> caloGeometry_token_;
  std::string clusterFilter_;
  std::string iteration_label_;
  std::unique_ptr<const ticl::ClusterFilterBase> theFilter_;
  hgcal::RecHitTools rhtools_;
};

DEFINE_FWK_MODULE(FilteredLayerClustersProducer);

FilteredLayerClustersProducer::FilteredLayerClustersProducer(const edm::ParameterSet& ps) {
  clusters_token_ = consumes<std::vector<reco::CaloCluster>>(ps.getParameter<edm::InputTag>("LayerClusters"));
  clustersMask_token_ = consumes<std::vector<float>>(ps.getParameter<edm::InputTag>("LayerClustersInputMask"));
  caloGeometry_token_ = esConsumes<CaloGeometry, CaloGeometryRecord, edm::Transition::BeginRun>();
  clusterFilter_ = ps.getParameter<std::string>("clusterFilter");
  theFilter_ = ClusterFilterFactory::get()->create(clusterFilter_, ps);
  iteration_label_ = ps.getParameter<std::string>("iteration_label");
  produces<std::vector<float>>(iteration_label_);
}

void FilteredLayerClustersProducer::beginRun(edm::Run const&, edm::EventSetup const& es) {
  edm::ESHandle<CaloGeometry> geom = es.getHandle(caloGeometry_token_);
  rhtools_.setGeometry(*geom);
}

void FilteredLayerClustersProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("LayerClusters", edm::InputTag("hgcalMergeLayerClusters"));
  desc.add<edm::InputTag>("LayerClustersInputMask",
                          edm::InputTag("hgcalMergeLayerClusters", "InitialLayerClustersMask"));
  desc.add<std::string>("iteration_label", "iterationLabelGoesHere");
  desc.add<std::string>("clusterFilter", "ClusterFilterByAlgoAndSize");
  desc.add<std::vector<int>>(
      "algo_number",
      {reco::CaloCluster::hgcal_em, reco::CaloCluster::hgcal_had, reco::CaloCluster::hgcal_scintillator});  // 6,7,8
  desc.add<int>("min_cluster_size", 0);
  desc.add<int>("max_cluster_size", 9999);
  desc.add<int>("min_layerId", 0);
  desc.add<int>("max_layerId", 9999);
  descriptions.add("filteredLayerClustersProducer", desc);
}

void FilteredLayerClustersProducer::produce(edm::Event& evt, const edm::EventSetup& es) {
  edm::Handle<std::vector<reco::CaloCluster>> clusterHandle;
  edm::Handle<std::vector<float>> inputClustersMaskHandle;
  evt.getByToken(clusters_token_, clusterHandle);
  evt.getByToken(clustersMask_token_, inputClustersMaskHandle);

  // Protection against missing input collections
  if (!clusterHandle.isValid() || !inputClustersMaskHandle.isValid()) {
    edm::LogWarning("FilteredLayerClustersProducer") << "Missing input collections. Producing an empty mask.";

    // Produce an empty mask and exit
    auto emptyMask = std::make_unique<std::vector<float>>();
    evt.put(std::move(emptyMask), iteration_label_);
    return;
  }

  const auto& inputClusterMask = *inputClustersMaskHandle;

  // Transfer input mask in output
  auto layerClustersMask = std::make_unique<std::vector<float>>(inputClusterMask);

  const auto& layerClusters = *clusterHandle;
  if (theFilter_) {
    theFilter_->filter(layerClusters, *layerClustersMask, rhtools_);
  }

  evt.put(std::move(layerClustersMask), iteration_label_);
}
