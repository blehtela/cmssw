import FWCore.ParameterSet.Config as cms
from HLTrigger.Configuration.common import producers_by_type

import os
from CondCore.CondDB.CondDB_cfi import CondDB as _CondDB

from CommonTools.PileupAlgos.Puppi_cff import puppi as _puppi, puppiNoLep as _puppiNoLep

ONLINE_OFFLINE_PUPROXY_SF = 0.0027

def usePFHCsAndJECs(process, DBFile):
    
    process.hltParticleFlow.calibrationsLabel = '' # For now use the standard label for Offline-PFHC in GT

    if os.path.exists(DBFile) and os.path.isfile(DBFile):
        #print(f"Using file: {DBFile} for the JECs")
        process.jescESSource = cms.ESSource('PoolDBESSource',
            _CondDB.clone(connect = 'sqlite_file:'+DBFile),
            toGet = cms.VPSet(
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK4PFHLT'),
                    label = cms.untracked.string('AK4PFHLT'),
                ),
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK8PFHLT'),
                    label = cms.untracked.string('AK8PFHLT'),
                ),
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK4PFchsHLT'),
                    label = cms.untracked.string('AK4PFchsHLT'),
                ),
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK8PFchsHLT'),
                    label = cms.untracked.string('AK8PFchsHLT'),
                ),
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK4PFPuppiHLT'),
                    label = cms.untracked.string('AK4PFPuppiHLT'),
                ),
                cms.PSet(
                    record = cms.string('JetCorrectionsRecord'),
                    tag = cms.string('JetCorrectorParametersCollection_Run3Winter23Digi_AK8PFPuppiHLT'),
                    label = cms.untracked.string('AK8PFPuppiHLT'),
                ),
            ),
        )

        process.jescESPrefer = cms.ESPrefer('PoolDBESSource', 'jescESSource')
    else:
        print(f"File for JECs does not exist: {DBFile}")
    
    return process

# This is a customization function that adjusts the existsing modules of the menu to add mixed tracking in a minimal way
def customizeHLTForMixedPF(process):

    # change the JECs
    # process = usePFHCsAndJECs(process, DBFile="/afs/cern.ch/work/t/tchatzis/private/run3_2023/CMSSW_13_2_3/src/JMETriggerAnalysis/NTuplizers/test/Run3Winter23Digi_MixedTrk.db")

    # Not affecting the other seed producers
    for producer in producers_by_type(process, "SeedGeneratorFromProtoTracksEDProducer"):
        producer.produceComplement = cms.bool(False)

    # Customization for the iter0 seeds
    process.hltIter0PFLowPixelSeedsFromPixelTracks.produceComplement = cms.bool(True)

    # Apply cuts for pixel tracks complement
    ## Quadraplets only to reduce timing (not very big impact in performance)
    process.hltPixelPUTracks = cms.EDProducer( "TrackWithVertexSelector",
        normalizedChi2 = cms.double( 999999.0 ),
        numberOfValidHits = cms.uint32( 0 ),
        zetaVtx = cms.double( 0.3 ),
        rhoVtx = cms.double( 0.2 ),
        ptErrorCut = cms.double( 5.0 ),
        dzMax = cms.double( 999.0 ),
        etaMin = cms.double( 0.0 ),
        etaMax = cms.double( 2.5 ), # choose only tracks from central region - no extention of tracker up to 2.7
        quality = cms.string( "highPurity" ), ##loose, tight, highPurity
        copyTrajectories = cms.untracked.bool( False ),
        nSigmaDtVertex = cms.double( 0.0 ),
        timesTag = cms.InputTag( "" ),
        ptMin = cms.double( 0.5 ), # minimum pT cut (this is the one used for Pixel Vertexing - 0.5 GeV)
        ptMax = cms.double( 10.0 ), # maximum pT cut 
        d0Max = cms.double( 999.0 ),
        copyExtras = cms.untracked.bool( False ),
        nVertices = cms.uint32( 2 ),
        vertexTag = cms.InputTag( "hltPixelVertices" ),
        src = cms.InputTag( "hltIter0PFLowPixelSeedsFromPixelTracks" ), # the complement reco::TrackCollection
        vtxFallback = cms.bool( True ),
        numberOfLostHits = cms.uint32( 999 ),
        numberOfValidPixelHits = cms.uint32( 3 ), # for now keeping everything 
        timeResosTag = cms.InputTag( "" ),
        useVtx = cms.bool( False ) ## Turning off vertex selection
    )
    
    # Doing it only for triplets i.e. classic Patatrack tracks - for doublets for Doublet Recover(BPix/FPix) there is no need to do it.
    #process.HLTIterativeTrackingIteration0 = cms.Sequence(process.hltIter0PFLowPixelSeedsFromPixelTracks+process.hltPixelPUTracks+process.hltIter0PFlowCkfTrackCandidates+process.hltIter0PFlowCtfWithMaterialTracks+process.hltIter0PFlowTrackCutClassifier+process.hltIter0PFlowTrackSelectionHighPurity)
    process.HLTIterativeTrackingIteration0.insert(process.HLTIterativeTrackingIteration0.index(process.hltIter0PFLowPixelSeedsFromPixelTracks)+1, process.hltPixelPUTracks)

    # Merging Iter0 tracks with the complement of pixel tracks
    process.hltPFTracks = cms.EDProducer( "TrackListMerger",
        ShareFrac = cms.double( 0.19 ),
        FoundHitBonus = cms.double( 5.0 ),
        LostHitPenalty = cms.double( 20.0 ),
        MinPT = cms.double( 0.05 ),
        Epsilon = cms.double( -0.001 ),
        MaxNormalizedChisq = cms.double( 1000.0 ),
        MinFound = cms.int32( 3 ),
        TrackProducers = cms.VInputTag( 'hltPixelPUTracks','hltPFMuonMerging' ),
        hasSelector = cms.vint32( 0, 0),
        indivShareFrac = cms.vdouble( 1.0, 1.0),
        selectedTrackQuals = cms.VInputTag( 'hltPixelPUTracks','hltPFMuonMerging' ),
        setsToMerge = cms.VPSet(
          cms.PSet(  pQual = cms.bool( False ),
            tLists = cms.vint32( 0, 1)
          )
        ),
        trackAlgoPriorityOrder = cms.string( "hltESPTrackAlgoPriorityOrder" ),
        allowFirstHitShare = cms.bool( True ),
        newQuality = cms.string( "confirmed" ),
        copyExtras = cms.untracked.bool( True ),
        writeOnlyTrkQuals = cms.bool( False ),
        copyMVA = cms.bool( False )
    )
    
    #process.HLTTrackReconstructionForPF = cms.Sequence(process.HLTDoLocalPixelSequence+process.HLTRecopixelvertexingSequence+process.HLTDoLocalStripSequence+process.HLTIterativeTrackingIter02+process.hltPFMuonMerging+process.hltPFTracks+process.hltMuonLinks+process.hltMuons)
    process.HLTTrackReconstructionForPF.insert(process.HLTTrackReconstructionForPF.index(process.hltPFMuonMerging)+1, process.hltPFTracks)
    
    # simple test to effectively remove the effect of doublet recovery iteration
    # process.hltPFMuonMerging.TrackProducers = cms.VInputTag("hltIterL3MuonTracks", "hltIter0PFlowTrackSelectionHighPurity")
    # process.hltPFMuonMerging.selectedTrackQuals = cms.VInputTag("hltIterL3MuonTracks", "hltIter0PFlowTrackSelectionHighPurity")

    # change to use separate hltLightPFTracks for Taus
    # process.hltLightPFTracksForTaus = process.hltLightPFTracks.clone()

    # for iImporter in process.hltParticleFlowBlockForTaus.elementImporters:
    #     if iImporter.importerName == cms.string('GeneralTracksImporter'):
    #         iImporter.source = 'hltLightPFTracksForTaus'
    
    # process.HLTParticleFlowSequenceForTaus = cms.Sequence(process.HLTPreshowerSequence+process.hltParticleFlowRecHitECALUnseeded+process.hltParticleFlowRecHitHBHE+process.hltParticleFlowRecHitHF+process.hltParticleFlowRecHitPSUnseeded+process.hltParticleFlowClusterECALUncorrectedUnseeded+process.hltParticleFlowClusterPSUnseeded+process.hltParticleFlowClusterECALUnseeded+process.hltParticleFlowClusterHBHE+process.hltParticleFlowClusterHCAL+process.hltParticleFlowClusterHF+process.hltLightPFTracksForTaus+process.hltParticleFlowBlockForTaus+process.hltParticleFlowForTaus)
    
    # use the mixed tracks collection for particle flow
    process.hltLightPFTracks.TkColList = cms.VInputTag("hltPFTracks")
    
    # Do not need this if not using PFVertices. It is better to use them though since it would allow the PUPPI algorithm to exploit vertex fit instead of simple DZ cut.
    # This is better for B-tagging. 
    # Customize the full hlt vertices such that they do not use the complement tracks by requiring at least 1 valid strip hit
    process.hltVerticesPF.TrackLabel = cms.InputTag("hltPFTracks")
    process.hltVerticesPF.TkFilterParameters.minValidStripHits = cms.int32(1)

    # Add the PFTracks in HLTTrackingForBeamspot
    #process.HLTTrackingForBeamSpot = cms.Sequence(process.HLTPreAK4PFJetsRecoSequence+process.HLTL2muonrecoSequence+process.HLTL3muonrecoSequence+process.HLTDoLocalPixelSequence+process.HLTRecopixelvertexingSequence+process.HLTDoLocalStripSequence+process.HLTIterativeTrackingIter02+process.hltPFMuonMerging+process.hltPFTracks)
    process.HLTTrackingForBeamSpot += process.hltPFTracks

    return process





# This function converts all PF jets to PF+PUPPI jets.
# i.e. all paths in the menu will use PUPPI.
def convertPFJetsToPUPPI(process):
    # change tracking to Mixed tracking
    process = customizeHLTForMixedPF(process)

    # calculate the number of pixel clusters as a proxy of PU
    process.hltPixelClustersMultiplicity = cms.EDProducer("HLTSiPixelClusterMultiplicityValueProducer",
        defaultValue = cms.double(-1.0),
        mightGet = cms.optional.untracked.vstring,
        src = cms.InputTag("siPixelClusters")
    )
    
    ## Modifications for Jets
    process.hltPFPuppi = _puppi.clone(
      candName = 'hltParticleFlow',
      UseDeltaZCut = True,
      EtaMinUseDeltaZ = 0.0,
      DeltaZCut = 0.3,
      #UseFromPVLooseTight = True,
      #   vtxNdofCut = 4,
      #   vtxZCut=24,
      UseDeltaZCutForPileup = True,
      vertexName = 'hltVerticesPF',
      #vertexName = 'hltPixelVertices',
      usePUProxyValue = True,
      PUProxyValue = 'hltPixelClustersMultiplicity',
      #NumOfPUVtxsForCharged = 0,
      useVertexAssociation = False,
      #NumOfPUVtxsForCharged = 2,  # from any vertex apply dz cut 
      #DeltaZCutForChargedFromPUVtxs = 1000.0
      #PtMaxNeutralsStartSlope = 10.0,
      #PtMaxNeutrals = 190.0,
    )
                    
    # note: here adding also MET/METNoMu PUPPI producers
    process.hltPFPuppiNoLep = process.hltPFPuppi.clone(
        puppiNoLep = cms.bool(True)
    )

    process.hltPFPuppiNoLepNoMu = process.hltPFPuppiNoLep.clone(
        candName = cms.InputTag("hltParticleFlowNoMu")
    )

    ## Modify the PUPPI A,B parameters
    for mod_i in [process.hltPFPuppi, process.hltPFPuppiNoLep, process.hltPFPuppiNoLepNoMu]:
      for algo_idx in range(len(mod_i.algos)):
        if len(mod_i.algos[algo_idx].MinNeutralPt) != len(mod_i.algos[algo_idx].MinNeutralPtSlope):
          raise RuntimeError('instance of PuppiProducer is misconfigured:\n\n'+str(mod_i)+' = '+mod_i.dumpPython())

        for algoReg_idx in range(len(mod_i.algos[algo_idx].MinNeutralPt)):
          mod_i.algos[algo_idx].MinNeutralPtSlope[algoReg_idx] *= ONLINE_OFFLINE_PUPROXY_SF

    ## convert AK4 jets to PUPPI ones by adding the PUPPI weights
    process.hltAK4PFJets.srcWeights = cms.InputTag("hltPFPuppi")
    process.hltAK4PFJets.applyWeight = cms.bool(True)

    # modify the PF sequence to add calculation of the PUPPI weights    
    process.HLTAK4PFJetsReconstructionSequence = cms.Sequence(
        process.HLTL2muonrecoSequence
      + process.HLTL3muonrecoSequence
      + process.HLTTrackReconstructionForPF
      + process.HLTParticleFlowSequence
      + process.hltVerticesPF
      + process.hltPixelClustersMultiplicity ##
      + process.hltPFPuppi ##
      + process.hltPFPuppiNoLep ##
      + process.hltParticleFlowNoMu ## 
      + process.hltPFPuppiNoLepNoMu ##
      + process.hltAK4PFJets
      + process.hltAK4PFJetsLooseID
      + process.hltAK4PFJetsTightID
    )
    
    process.HLTAK8PFJetsReconstructionSequence = cms.Sequence(
        process.HLTL2muonrecoSequence
       +process.HLTL3muonrecoSequence
       +process.HLTTrackReconstructionForPF
       +process.HLTParticleFlowSequence
       + process.hltVerticesPF
       + process.hltPixelClustersMultiplicity ##
       + process.hltPFPuppi ##
       + process.hltPFPuppiNoLep ##
       + process.hltParticleFlowNoMu ## 
       + process.hltPFPuppiNoLepNoMu ##
       +process.hltAK8PFJets
     )

    # change the JECs for corrected Jets tags
    # process.hltAK4PFFastJetCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    # process.hltAK4PFRelativeCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    # process.hltAK4PFAbsoluteCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    # process.hltAK4PFResidualCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    
    # process.hltAK4PFFastJetCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFRelativeCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFAbsoluteCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFResidualCorrector.algorithm = cms.string('AK8PFPuppiHLT')

    # add changes here for AK8
    ## convert AK8 jets to PUPPI ones by adding the PUPPI weights
    # process.hltAK8PFJets.srcWeights = cms.InputTag("hltPFPuppi")
    # process.hltAK8PFJets.applyWeight = cms.bool(True)

    # change the JECs for corrected Jets tags
    # process.hltAK8PFFastJetCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFRelativeCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFAbsoluteCorrector.algorithm = cms.string('AK8PFPuppiHLT')
    # process.hltAK8PFResidualCorrector.algorithm = cms.string('AK8PFPuppiHLT')


    ## Modifications for MET
    process.hltPFMETProducer.srcWeights = cms.InputTag("hltPFPuppiNoLep")
    process.hltPFMETProducer.applyWeight = cms.bool(True)
    process.hltPFMETNoMuProducer.srcWeights = cms.InputTag("hltPFPuppiNoLepNoMu")
    process.hltPFMETNoMuProducer.applyWeight = cms.bool(True)

    
    return process

# This function converts all PF jets to PF
# +CHS jets.
# i.e. all paths in the menu will use CHS.
def convertPFJetsToCHS(process):
    # change tracking to Mixed tracking
    process = customizeHLTForMixedPF(process)
    
    ## Modifications for Jets
    process.hltParticleFlowPtrs = cms.EDProducer("PFCandidateFwdPtrProducer",
        src = cms.InputTag("hltParticleFlow")
    )

    process.hltPFPileUpJME = cms.EDProducer("PFPileUp",
        DzCutForChargedFromPUVtxs = cms.double(0.3),
        NumOfPUVtxsForCharged = cms.uint32(0),
        PFCandidates = cms.InputTag("hltParticleFlowPtrs"),
        Vertices = cms.InputTag("hltPixelVertices"),
        checkClosestZVertex = cms.bool(True),
        enable = cms.bool(True),
        mightGet = cms.optional.untracked.vstring,
        useVertexAssociation = cms.bool(False),
        verbose = cms.untracked.bool(False),
        vertexAssociation = cms.InputTag(""),
        vertexAssociationQuality = cms.int32(0)
    )
    
    process.hltPFNoPileUpJME = cms.EDProducer("TPPFCandidatesOnPFCandidates",
        bottomCollection = cms.InputTag("hltParticleFlowPtrs"),
        enable = cms.bool(True),
        matchByPtrDirect = cms.bool(True),
        mightGet = cms.optional.untracked.vstring,
        name = cms.untracked.string('pileUpOnPFCandidates'),
        topCollection = cms.InputTag("hltPFPileUpJME")
    )
    
    ## for MET
    process.hltParticleFlowCHS = cms.EDProducer('FwdPtrRecoPFCandidateConverter',
      src = cms.InputTag("hltPFNoPileUpJME")
    )
    
    ## for METNoMu
    process.hltParticleFlowNoMuPtrs = cms.EDProducer("PFCandidateFwdPtrProducer",
        src = cms.InputTag("hltParticleFlowNoMu")
    )
    process.hltPFNoMuPileUpJME = process.hltPFPileUpJME.clone(PFCandidates = cms.InputTag("hltParticleFlowNoMuPtrs"))
    process.hltPFNoMuNoPileUpJME = process.hltPFNoPileUpJME.clone(
        bottomCollection = cms.InputTag("hltParticleFlowNoMuPtrs"),
        topCollection = cms.InputTag("hltPFNoMuPileUpJME")
    )

    process.hltParticleFlowNoMuCHS = cms.EDProducer('FwdPtrRecoPFCandidateConverter',
      src = cms.InputTag("hltPFNoMuNoPileUpJME")
    )

    # modify the PF sequence to add calculation of the PUPPI weights    
    process.HLTAK4PFJetsReconstructionSequence = cms.Sequence(process.HLTL2muonrecoSequence
      + process.HLTL3muonrecoSequence
      + process.HLTTrackReconstructionForPF
      + process.HLTParticleFlowSequence
      + process.hltVerticesPF
      + process.hltParticleFlowPtrs ##
      + process.hltPFPileUpJME ##
      + process.hltPFNoPileUpJME ##
      + process.hltParticleFlowCHS ##
      + process.hltParticleFlowNoMu ##
      + process.hltParticleFlowNoMuPtrs ##
      + process.hltPFNoMuPileUpJME ##
      + process.hltPFNoMuNoPileUpJME ##
      + process.hltParticleFlowNoMuCHS ##
      + process.hltAK4PFJets
      + process.hltAK4PFJetsLooseID
      + process.hltAK4PFJetsTightID
    )
    ## convert AK4 jets to PUPPI ones by adding the PUPPI weights
    process.hltAK4PFJets.src = cms.InputTag("hltPFNoPileUpJME")

    # change the JECs for corrected Jets tags
    process.hltAK4PFFastJetCorrector.algorithm = cms.string('AK4PFchsHLT')
    process.hltAK4PFRelativeCorrector.algorithm = cms.string('AK4PFchsHLT')
    process.hltAK4PFAbsoluteCorrector.algorithm = cms.string('AK4PFchsHLT')
    process.hltAK4PFResidualCorrector.algorithm = cms.string('AK4PFchsHLT')
    
    # changes here for AK8
    # ## convert AK8 jets to PUPPI ones by adding the PUPPI weights
    # process.hltAK8PFJets.src = cms.InputTag("hltPFNoPileUpJME")

    # # change the JECs for corrected Jets tags
    # process.hltAK8PFFastJetCorrector.algorithm = cms.string('AK8PFchsHLT')
    # process.hltAK8PFRelativeCorrector.algorithm = cms.string('AK8PFchsHLT')
    # process.hltAK8PFAbsoluteCorrector.algorithm = cms.string('AK8PFchsHLT')
    # process.hltAK8PFResidualCorrector.algorithm = cms.string('AK8PFchsHLT')


    ## Modifications for MET
    process.hltPFMETProducer.src = cms.InputTag('hltParticleFlowCHS')
    process.hltPFMETNoMuProducer.src = cms.InputTag("hltParticleFlowNoMuCHS")
    
    return process



def addPaths_MC_JMEPFPuppi(process,listOfPaths):

    process.hltPreMCJMEPFPuppi = cms.EDFilter('HLTPrescaler',
      L1GtReadoutRecordTag = cms.InputTag('hltGtStage2Digis'),
      offset = cms.uint32(0)
    )

    process.hltPixelClustersMultiplicity = cms.EDProducer("HLTSiPixelClusterMultiplicityValueProducer",
        defaultValue = cms.double(-1.0),
        mightGet = cms.optional.untracked.vstring,
        src = cms.InputTag("siPixelClusters")
    )

    process.hltPFPuppi = _puppi.clone(
      candName = 'hltParticleFlow',
      UseDeltaZCut = True,
      EtaMinUseDeltaZ = 0.0,
      DeltaZCut = 0.3,
      #UseFromPVLooseTight = True,
      #   vtxNdofCut = 4,
      #   vtxZCut=24,
      UseDeltaZCutForPileup = True,
      vertexName = 'hltVerticesPF',
      #vertexName = 'hltPixelVertices',
      usePUProxyValue = True,
      PUProxyValue = 'hltPixelClustersMultiplicity',
      #NumOfPUVtxsForCharged = 0,
      useVertexAssociation = False,
      #NumOfPUVtxsForCharged = 2,  # from any vertex apply dz cut 
      #DeltaZCutForChargedFromPUVtxs = 1000.0
      #PtMaxNeutralsStartSlope = 10.0,
      #PtMaxNeutrals = 190.0,
    )
                    
    # note: here adding also MET/METNoMu PUPPI producers
    process.hltPFPuppiNoLep = process.hltPFPuppi.clone(
        puppiNoLep = cms.bool(True)
    )

    process.hltPFPuppiNoLepNoMu = process.hltPFPuppiNoLep.clone(
        candName = cms.InputTag("hltParticleFlowNoMu")
    )

    ## Modify the PUPPI A,B parameters
    for mod_i in [process.hltPFPuppi, process.hltPFPuppiNoLep, process.hltPFPuppiNoLepNoMu]:
      for algo_idx in range(len(mod_i.algos)):
        if len(mod_i.algos[algo_idx].MinNeutralPt) != len(mod_i.algos[algo_idx].MinNeutralPtSlope):
          raise RuntimeError('instance of PuppiProducer is misconfigured:\n\n'+str(mod_i)+' = '+mod_i.dumpPython())

        for algoReg_idx in range(len(mod_i.algos[algo_idx].MinNeutralPt)):
          mod_i.algos[algo_idx].MinNeutralPtSlope[algoReg_idx] *= ONLINE_OFFLINE_PUPROXY_SF

    """
    process.hltPFPuppi = cms.EDProducer("PuppiProducer",
        DeltaZCut = cms.double(0.3),
        DeltaZCutForChargedFromPUVtxs = cms.double(0.2),
        EtaMaxCharged = cms.double(99999),
        EtaMaxPhotons = cms.double(2.5),
        EtaMinUseDeltaZ = cms.double(0.0),
        MinPuppiWeight = cms.double(0.01),
        NumOfPUVtxsForCharged = cms.uint32(2),
        PUProxyValue = cms.InputTag("hltPixelClustersMultiplicity"),
        PtMaxCharged = cms.double(20.0),
        PtMaxNeutrals = cms.double(200),
        PtMaxNeutralsStartSlope = cms.double(20.0),
        PtMaxPhotons = cms.double(-1),
        UseDeltaZCut = cms.bool(True),
        UseDeltaZCutForPileup = cms.bool(True),
        UseFromPVLooseTight = cms.bool(False),
        algos = cms.VPSet(
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                MedEtaSF = cms.vdouble(1.0, 1.0),
                MinNeutralPt = cms.vdouble(0.2, 0.2),
                MinNeutralPtSlope = cms.vdouble(1.62e-05, 1.62e-05),
                RMSEtaSF = cms.vdouble(1.0, 1.0),
                etaMax = cms.vdouble(1.3, 2.5),
                etaMin = cms.vdouble(0.0, 1.3),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.1),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(True)
                ))
            ),
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                MedEtaSF = cms.vdouble(1.1, 1.05),
                MinNeutralPt = cms.vdouble(1.7, 2.0),
                MinNeutralPtSlope = cms.vdouble(0.0008640000000000001, 0.00027),
                RMSEtaSF = cms.vdouble(1.3, 0.4),
                etaMax = cms.vdouble(3.0, 10.0),
                etaMin = cms.vdouble(2.5, 3.0),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.5),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(False)
                ))
            )
        ),
        applyCHS = cms.bool(True),
        candName = cms.InputTag("hltParticleFlow"),
        clonePackedCands = cms.bool(False),
        invertPuppi = cms.bool(False),
        mightGet = cms.optional.untracked.vstring,
        puppiDiagnostics = cms.bool(False),
        puppiNoLep = cms.bool(False),
        useExistingWeights = cms.bool(False),
        useExp = cms.bool(False),
        usePUProxyValue = cms.bool(True),
        useVertexAssociation = cms.bool(False),
        vertexAssociation = cms.InputTag(""),
        vertexAssociationQuality = cms.int32(0),
        vertexName = cms.InputTag("hltVerticesPF"),
        vtxNdofCut = cms.int32(4),
        vtxZCut = cms.double(24)
    )
    """

    process.HLTPFPuppiSequence = cms.Sequence(
        process.HLTPreAK4PFJetsRecoSequence
      + process.HLTL2muonrecoSequence
      + process.HLTL3muonrecoSequence
      + process.HLTTrackReconstructionForPF
      + process.HLTParticleFlowSequence
      + process.hltVerticesPF
      + process.hltPixelClustersMultiplicity
      + process.hltPFPuppi
    )

    ## AK4
    process.hltAK4PFPuppiJets = process.hltAK4PFJets.clone(
      src = 'hltParticleFlow',
      srcWeights = 'hltPFPuppi',
      applyWeight = True,
    )

    process.hltAK4PFPuppiJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK4PFPuppiJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK4PFPuppiJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK4PFPuppiJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK4PFPuppiJetCorrectorL1',
        'hltAK4PFPuppiJetCorrectorL2',
        'hltAK4PFPuppiJetCorrectorL3',
      ),
    )

    process.hltAK4PFPuppiJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK4PFPuppiJets'),
      correctors = cms.VInputTag('hltAK4PFPuppiJetCorrector'),
    )

    process.HLTAK4PFPuppiJetsSequence = cms.Sequence(
        process.hltAK4PFPuppiJets
      + process.hltAK4PFPuppiJetCorrectorL1
      + process.hltAK4PFPuppiJetCorrectorL2
      + process.hltAK4PFPuppiJetCorrectorL3
      + process.hltAK4PFPuppiJetCorrector
      + process.hltAK4PFPuppiJetsCorrected
    )

    ## AK8
    process.hltAK8PFPuppiJets = process.hltAK8PFJets.clone(
      src = 'hltParticleFlow',
      srcWeights = 'hltPFPuppi',
      applyWeight = True,
    )

    process.hltAK8PFPuppiJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK8PFPuppiJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK8PFPuppiJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK8PFPuppiJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK8PFPuppiJetCorrectorL1',
        'hltAK8PFPuppiJetCorrectorL2',
        'hltAK8PFPuppiJetCorrectorL3',
      ),
    )

    process.hltAK8PFPuppiJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK8PFPuppiJets'),
      correctors = cms.VInputTag('hltAK8PFPuppiJetCorrector'),
    )

    process.HLTAK8PFPuppiJetsSequence = cms.Sequence(
        process.hltAK8PFPuppiJets
      + process.hltAK8PFPuppiJetCorrectorL1
      + process.hltAK8PFPuppiJetCorrectorL2
      + process.hltAK8PFPuppiJetCorrectorL3
      + process.hltAK8PFPuppiJetCorrector
      + process.hltAK8PFPuppiJetsCorrected
    )

    ## MET
    """
    process.hltPFPuppiNoLep = cms.EDProducer("PuppiProducer",
        DeltaZCut = cms.double(0.3),
        DeltaZCutForChargedFromPUVtxs = cms.double(0.2),
        EtaMaxCharged = cms.double(99999),
        EtaMaxPhotons = cms.double(2.5),
        EtaMinUseDeltaZ = cms.double(0.0),
        MinPuppiWeight = cms.double(0.01),
        NumOfPUVtxsForCharged = cms.uint32(2),
        PUProxyValue = cms.InputTag("hltPixelClustersMultiplicity"),
        PtMaxCharged = cms.double(20.0),
        PtMaxNeutrals = cms.double(200),
        PtMaxNeutralsStartSlope = cms.double(20.0),
        PtMaxPhotons = cms.double(-1),
        UseDeltaZCut = cms.bool(True),
        UseDeltaZCutForPileup = cms.bool(True),
        UseFromPVLooseTight = cms.bool(False),
        algos = cms.VPSet(
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                MedEtaSF = cms.vdouble(1.0, 1.0),
                MinNeutralPt = cms.vdouble(0.2, 0.2),
                MinNeutralPtSlope = cms.vdouble(1.62e-05, 1.62e-05),
                RMSEtaSF = cms.vdouble(1.0, 1.0),
                etaMax = cms.vdouble(1.3, 2.5),
                etaMin = cms.vdouble(0.0, 1.3),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.1),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(True)
                ))
            ),
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                MedEtaSF = cms.vdouble(1.1, 1.05),
                MinNeutralPt = cms.vdouble(1.7, 2.0),
                MinNeutralPtSlope = cms.vdouble(0.0008640000000000001, 0.00027),
                RMSEtaSF = cms.vdouble(1.3, 0.4),
                etaMax = cms.vdouble(3.0, 10.0),
                etaMin = cms.vdouble(2.5, 3.0),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.5),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(False)
                ))
            )
        ),
        applyCHS = cms.bool(True),
        candName = cms.InputTag("hltParticleFlow"),
        clonePackedCands = cms.bool(False),
        invertPuppi = cms.bool(False),
        mightGet = cms.optional.untracked.vstring,
        puppiDiagnostics = cms.bool(False),
        puppiNoLep = cms.bool(True),
        useExistingWeights = cms.bool(False),
        useExp = cms.bool(False),
        usePUProxyValue = cms.bool(True),
        useVertexAssociation = cms.bool(False),
        vertexAssociation = cms.InputTag(""),
        vertexAssociationQuality = cms.int32(0),
        vertexName = cms.InputTag("hltVerticesPF"),
        vtxNdofCut = cms.int32(4),
        vtxZCut = cms.double(24)
    )
    """
    process.hltPFPuppiMET = cms.EDProducer('PFMETProducer',
      alias = cms.string(''),
      applyWeight = cms.bool(True),
      calculateSignificance = cms.bool(False),
      globalThreshold = cms.double(0.0),
      parameters = cms.PSet(),
      src = cms.InputTag('hltParticleFlow'),
      srcWeights = cms.InputTag('hltPFPuppiNoLep'),
    )

    ## MET Type-1
    process.hltPFPuppiMETCorrection = cms.EDProducer('PFJetMETcorrInputProducer',
      jetCorrEtaMax = cms.double(9.9),
      jetCorrLabel = cms.InputTag('hltAK4PFPuppiJetCorrector'),
      jetCorrLabelRes = cms.InputTag('hltAK4PFPuppiJetCorrector'),
      offsetCorrLabel = cms.InputTag('hltAK4PFPuppiJetCorrectorL1'),
      skipEM = cms.bool(True),
      skipEMfractionThreshold = cms.double(0.9),
      skipMuonSelection = cms.string('isGlobalMuon | isStandAloneMuon'),
      skipMuons = cms.bool(True),
      src = cms.InputTag('hltAK4PFPuppiJets'),
      type1JetPtThreshold = cms.double(30.0),
    )

    process.hltPFPuppiMETTypeOne = cms.EDProducer('CorrectedPFMETProducer',
      src = cms.InputTag('hltPFPuppiMET'),
      srcCorrections = cms.VInputTag('hltPFPuppiMETCorrection:type1'),
    )

    process.HLTPFPuppiMETSequence = cms.Sequence(
        process.hltPFPuppiNoLep
      + process.hltPFPuppiMET
      + process.hltPFPuppiMETCorrection
      + process.hltPFPuppiMETTypeOne
    )

    ## Paths

    # Reconstruction path
    process.MC_JMEPFPuppi_v1 = cms.Path(
        process.HLTBeginSequence
      + process.hltPreMCJMEPFPuppi
      + process.HLTPFPuppiSequence
      + process.HLTAK4PFPuppiJetsSequence
      + process.HLTAK8PFPuppiJetsSequence
      + process.HLTPFPuppiMETSequence
      + process.HLTEndSequence
    )

    #### HLT paths development area
    # example customization for creating HLT_PFPuppiJet40_v1 path
    ## HLT_PFPuppiJet40_v1
    process.hltPrePFPuppiJet40 = cms.EDFilter("HLTPrescaler",
        L1GtReadoutRecordTag = cms.InputTag("hltGtStage2Digis"),
        offset = cms.uint32(0)
    )

    process.hltPFPuppiJetsCorrectedMatchedToCaloJets10 = cms.EDProducer("HLTPFJetsMatchedToFilteredCaloJetsProducer",
        maxDeltaR = cms.double(0.5),
        src = cms.InputTag("hltAK4PFPuppiJetsCorrected"),
        triggerJetsFilter = cms.InputTag("hltSingleCaloJet10"),
        triggerJetsType = cms.int32(85)
    )

    process.hltSinglePFPuppiJet40 = cms.EDFilter("HLT1PFJet",
        MaxEta = cms.double(5.0),
        MaxMass = cms.double(-1.0),
        MinE = cms.double(-1.0),
        MinEta = cms.double(-1.0),
        MinMass = cms.double(-1.0),
        MinN = cms.int32(1),
        MinPt = cms.double(40.0),
        inputTag = cms.InputTag("hltPFPuppiJetsCorrectedMatchedToCaloJets10"),
        saveTags = cms.bool(True),
        triggerType = cms.int32(85)
    )


    process.HLT_PFPuppiJet40_v1 = cms.Path(
        process.SimL1Emulator
      + process.HLTBeginSequence 
      + process.hltL1sZeroBias                # L1 seed
      + process.hltPrePFPuppiJet40            # prescale filter
      + process.HLTAK4CaloJetsSequence        # produce calo jets
      + process.hltSingleCaloJet10            # filter calos > 10 GeV (for matching - see later)  
      + process.HLTPFPuppiSequence            # produce pf particles and puppi weights
      + process.HLTAK4PFPuppiJetsSequence     # make AK4 jets reconstruction using puppi weights + calibrations
      + process.hltPFPuppiJetsCorrectedMatchedToCaloJets10  # match puppi to calo jets with dR<0.5 
      + process.hltSinglePFPuppiJet40              # filter puppi jets with pT>40GeV
      + process.HLTEndSequence
    )
    
    ## adding paths in "trigger menu"
    # modify this list of names with any new path
    newPathNames = [
       'HLT_PFPuppiJet40_v1'
    ] 
    
    # Adds the paths in the menu
    for pathName in newPathNames:
       process.datasets.JetMET += cms.vstring(pathName)
       process.datasets.OnlineMonitor += cms.vstring(pathName)
       process.hltDatasetJetMET.triggerConditions += cms.vstring(pathName)
       process.hltDatasetOnlineMonitor.triggerConditions += cms.vstring(pathName + ' / 3')
       listOfPaths.append(pathName)
       
    # append new paths to schedule
    if process.schedule_():
      #process.schedule_().append(process.MC_JMEPFPuppi_v1)
      process.schedule_().append(process.HLT_PFPuppiJet40_v1)

    return [process,listOfPaths]




def addPaths_MC_JMEPFCHS(process):

    process.hltPreMCJMEPFCHS = cms.EDFilter('HLTPrescaler',
      L1GtReadoutRecordTag = cms.InputTag('hltGtStage2Digis'),
      offset = cms.uint32(0)
    )

    process.hltParticleFlowPtrs = cms.EDProducer("PFCandidateFwdPtrProducer",
        src = cms.InputTag("hltParticleFlow")
    )
    
    process.hltPFPileUpJME = cms.EDProducer("PFPileUp",
        DzCutForChargedFromPUVtxs = cms.double(0.3),
        NumOfPUVtxsForCharged = cms.uint32(0),
        PFCandidates = cms.InputTag("hltParticleFlowPtrs"),
        Vertices = cms.InputTag("hltPixelVertices"),
        checkClosestZVertex = cms.bool(True),
        enable = cms.bool(True),
        mightGet = cms.optional.untracked.vstring,
        useVertexAssociation = cms.bool(False),
        verbose = cms.untracked.bool(False),
        vertexAssociation = cms.InputTag(""),
        vertexAssociationQuality = cms.int32(0)
    )
    
    process.hltPFNoPileUpJME = cms.EDProducer("TPPFCandidatesOnPFCandidates",
        bottomCollection = cms.InputTag("hltParticleFlowPtrs"),
        enable = cms.bool(True),
        matchByPtrDirect = cms.bool(True),
        mightGet = cms.optional.untracked.vstring,
        name = cms.untracked.string('pileUpOnPFCandidates'),
        topCollection = cms.InputTag("hltPFPileUpJME")
    )

    process.HLTPFCHSSequence = cms.Sequence(
        process.HLTPreAK4PFJetsRecoSequence
      + process.HLTL2muonrecoSequence
      + process.HLTL3muonrecoSequence
      + process.HLTTrackReconstructionForPF
      + process.HLTParticleFlowSequence
      + process.hltParticleFlowPtrs
      + process.hltVerticesPF
      + process.hltPFPileUpJME
      + process.hltPFNoPileUpJME
    )

    ## AK4
    process.hltAK4PFCHSJets = process.hltAK4PFJets.clone(src = 'hltPFNoPileUpJME')

    process.hltAK4PFCHSJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK4PFchsHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK4PFCHSJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFchsHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK4PFCHSJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFchsHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK4PFCHSJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK4PFCHSJetCorrectorL1',
        'hltAK4PFCHSJetCorrectorL2',
        'hltAK4PFCHSJetCorrectorL3',
      ),
    )

    process.hltAK4PFCHSJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK4PFCHSJets'),
      correctors = cms.VInputTag('hltAK4PFCHSJetCorrector'),
    )

    process.HLTAK4PFCHSJetsSequence = cms.Sequence(
        process.hltAK4PFCHSJets
      + process.hltAK4PFCHSJetCorrectorL1
      + process.hltAK4PFCHSJetCorrectorL2
      + process.hltAK4PFCHSJetCorrectorL3
      + process.hltAK4PFCHSJetCorrector
      + process.hltAK4PFCHSJetsCorrected
    )

    ## AK8
    process.hltAK8PFCHSJets = process.hltAK4PFJets.clone(src = 'hltPFNoPileUpJME')

    process.hltAK8PFCHSJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK8PFchsHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK8PFCHSJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFchsHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK8PFCHSJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFchsHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK8PFCHSJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK8PFCHSJetCorrectorL1',
        'hltAK8PFCHSJetCorrectorL2',
        'hltAK8PFCHSJetCorrectorL3',
      ),
    )

    process.hltAK8PFCHSJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK8PFCHSJets'),
      correctors = cms.VInputTag('hltAK8PFCHSJetCorrector'),
    )

    process.HLTAK8PFCHSJetsSequence = cms.Sequence(
        process.hltAK8PFCHSJets
      + process.hltAK8PFCHSJetCorrectorL1
      + process.hltAK8PFCHSJetCorrectorL2
      + process.hltAK8PFCHSJetCorrectorL3
      + process.hltAK8PFCHSJetCorrector
      + process.hltAK8PFCHSJetsCorrected
    )

    ## MET
    process.hltParticleFlowCHS = cms.EDProducer('FwdPtrRecoPFCandidateConverter',
      src = process.hltAK4PFCHSJets.src,
    )

    process.hltPFCHSMET = cms.EDProducer('PFMETProducer',
      src = cms.InputTag('hltParticleFlowCHS'),
      globalThreshold = cms.double(0.0),
      calculateSignificance = cms.bool(False),
    )

    ## MET Type-1
    process.hltPFCHSMETCorrection = cms.EDProducer('PFJetMETcorrInputProducer',
      jetCorrEtaMax = cms.double(9.9),
      jetCorrLabel = cms.InputTag('hltAK4PFCHSJetCorrector'),
      jetCorrLabelRes = cms.InputTag('hltAK4PFCHSJetCorrector'),
      offsetCorrLabel = cms.InputTag('hltAK4PFCHSJetCorrectorL1'),
      skipEM = cms.bool(True),
      skipEMfractionThreshold = cms.double(0.9),
      skipMuonSelection = cms.string('isGlobalMuon | isStandAloneMuon'),
      skipMuons = cms.bool(True),
      src = cms.InputTag('hltAK4PFCHSJets'),
      type1JetPtThreshold = cms.double(30.0),
    )

    process.hltPFCHSMETTypeOne = cms.EDProducer('CorrectedPFMETProducer',
      src = cms.InputTag('hltPFCHSMET'),
      srcCorrections = cms.VInputTag('hltPFCHSMETCorrection:type1'),
    )

    ## Sequence: MET CHS
    process.HLTPFCHSMETSequence = cms.Sequence(
        process.hltParticleFlowCHS
      + process.hltPFCHSMET
      + process.hltPFCHSMETCorrection
      + process.hltPFCHSMETTypeOne
    )

    ## Path
    process.MC_JMEPFCHS_v1 = cms.Path(
        process.HLTBeginSequence
      + process.hltPreMCJMEPFCHS
      + process.HLTPFCHSSequence
      + process.HLTAK4PFCHSJetsSequence
      + process.HLTAK8PFCHSJetsSequence
      + process.HLTPFCHSMETSequence
      + process.HLTEndSequence
    )
    
    process.schedule.insert(0,process.MC_JMEPFCHS_v1)

    # if process.schedule_():
    #   print('adding CHS paths to schedule')
    #   process.schedule_().append(process.MC_JMEPFCHS_v1)

    return process

def addPaths_MC_JMEPFPuppi(process,listOfPaths=[]):

    process.hltPreMCJMEPFPuppi = cms.EDFilter('HLTPrescaler',
      L1GtReadoutRecordTag = cms.InputTag('hltGtStage2Digis'),
      offset = cms.uint32(0)
    )

    # calculate the number of pixel clusters as a proxy of PU
    process.hltPixelClustersMultiplicity = cms.EDProducer("HLTSiPixelClusterMultiplicityValueProducer",
        defaultValue = cms.double(-1.0),
        mightGet = cms.optional.untracked.vstring,
        src = cms.InputTag("siPixelClusters")
    )
    process.hltPFPuppi = _puppi.clone(
      candName = 'hltParticleFlow',
      UseDeltaZCut = True,
      EtaMinUseDeltaZ = 0.0,
      DeltaZCut = 0.3,
      #UseFromPVLooseTight = True,
      #   vtxNdofCut = 4,
      #   vtxZCut=24,
      UseDeltaZCutForPileup = True,
      vertexName = 'hltVerticesPF',
      #vertexName = 'hltPixelVertices',
      usePUProxyValue = True,
      PUProxyValue = 'hltPixelClustersMultiplicity',
      #NumOfPUVtxsForCharged = 0,
      useVertexAssociation = False,
      #NumOfPUVtxsForCharged = 2,  # from any vertex apply dz cut 
      #DeltaZCutForChargedFromPUVtxs = 1000.0
      #PtMaxNeutralsStartSlope = 10.0,
      #PtMaxNeutrals = 190.0,
    )
                    
    # note: here adding also MET/METNoMu PUPPI producers
    process.hltPFPuppiNoLep = process.hltPFPuppi.clone(
        puppiNoLep = cms.bool(True)
    )

    process.hltPFPuppiNoLepNoMu = process.hltPFPuppiNoLep.clone(
        candName = cms.InputTag("hltParticleFlowNoMu")
    )

    ## Modify the PUPPI A,B parameters
    for mod_i in [process.hltPFPuppi, process.hltPFPuppiNoLep, process.hltPFPuppiNoLepNoMu]:
      for algo_idx in range(len(mod_i.algos)):
        if len(mod_i.algos[algo_idx].MinNeutralPt) != len(mod_i.algos[algo_idx].MinNeutralPtSlope):
          raise RuntimeError('instance of PuppiProducer is misconfigured:\n\n'+str(mod_i)+' = '+mod_i.dumpPython())

        for algoReg_idx in range(len(mod_i.algos[algo_idx].MinNeutralPt)):
          mod_i.algos[algo_idx].MinNeutralPtSlope[algoReg_idx] *= ONLINE_OFFLINE_PUPROXY_SF
    
    """
    process.hltPFPuppi = cms.EDProducer("PuppiProducer",
        DeltaZCut = cms.double(0.3),
        DeltaZCutForChargedFromPUVtxs = cms.double(0.2),
        EtaMaxCharged = cms.double(99999),
        EtaMaxPhotons = cms.double(2.5),
        EtaMinUseDeltaZ = cms.double(0.0),
        MinPuppiWeight = cms.double(0.01),
        NumOfPUVtxsForCharged = cms.uint32(2),
        PUProxyValue = cms.InputTag("hltPixelClustersMultiplicity"),
        PtMaxCharged = cms.double(20.0),
        PtMaxNeutrals = cms.double(200),
        PtMaxNeutralsStartSlope = cms.double(20.0),
        PtMaxPhotons = cms.double(20.0),
        UseDeltaZCut = cms.bool(True),
        UseDeltaZCutForPileup = cms.bool(True),
        UseFromPVLooseTight = cms.bool(False),
        algos = cms.VPSet(
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                MedEtaSF = cms.vdouble(1.0, 1.0),
                MinNeutralPt = cms.vdouble(0.2, 0.2),
                MinNeutralPtSlope = cms.vdouble(4.86e-05, 8.1e-05),
                RMSEtaSF = cms.vdouble(1.0, 1.0),
                etaMax = cms.vdouble(1.3, 2.5),
                etaMin = cms.vdouble(0.0, 1.3),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.1),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(True)
                ))
            ),
            cms.PSet(
                EtaMaxExtrap = cms.double(2.0),
                #MedEtaSF = cms.vdouble(1.1, 1.05),
                MedEtaSF = cms.vdouble(0.9, 0.75),
                MinNeutralPt = cms.vdouble(1.7, 2.0),
                MinNeutralPtSlope = cms.vdouble(0.000216, 0.000216),#cms.vdouble(0.0008640000000000001, 0.0002025),
                #RMSEtaSF = cms.vdouble(1.3, 0.4),
                RMSEtaSF = cms.vdouble(1.2, 0.95),
                etaMax = cms.vdouble(3.0, 10.0),
                etaMin = cms.vdouble(2.5, 3.0),
                ptMin = cms.vdouble(0.0, 0.0),
                puppiAlgos = cms.VPSet(cms.PSet(
                    algoId = cms.int32(5),
                    applyLowPUCorr = cms.bool(True),
                    combOpt = cms.int32(0),
                    cone = cms.double(0.4),
                    rmsPtMin = cms.double(0.5),
                    rmsScaleFactor = cms.double(1.0),
                    useCharged = cms.bool(False)
                ))
            )
        ),
        applyCHS = cms.bool(True),
        candName = cms.InputTag("hltParticleFlow"),
        clonePackedCands = cms.bool(False),
        invertPuppi = cms.bool(False),
        mightGet = cms.optional.untracked.vstring,
        puppiDiagnostics = cms.bool(False),
        puppiNoLep = cms.bool(False),
        useExistingWeights = cms.bool(False),
        useExp = cms.bool(False),
        usePUProxyValue = cms.bool(True),
        useVertexAssociation = cms.bool(False),
        vertexAssociation = cms.InputTag(""),
        vertexAssociationQuality = cms.int32(0),
        vertexName = cms.InputTag("hltPixelVertices"), # Could use hltVerticesPF to use vertex fit information - but it seems problematic now.
        vtxNdofCut = cms.int32(4),
        vtxZCut = cms.double(24)
    )
    
    # note: here adding also MET/METNoMu PUPPI producers
    # normally for timing purposes of course would like to keep this separate - it is a waste of resources! 
    process.hltPFPuppiNoLep = process.hltPFPuppi.clone()
    process.hltPFPuppiNoLep.puppiNoLep = cms.bool(True)
    """
    process.HLTPFPuppiSequence = cms.Sequence(
        process.HLTPreAK4PFJetsRecoSequence
      + process.HLTL2muonrecoSequence
      + process.HLTL3muonrecoSequence
      + process.HLTTrackReconstructionForPF
      + process.HLTParticleFlowSequence
      + process.hltVerticesPF
      + process.hltPixelClustersMultiplicity
      + process.hltPFPuppi
    )

    ## AK4
    process.hltAK4PFPuppiJets = process.hltAK4PFJets.clone(
      src = 'hltParticleFlow',
      srcWeights = 'hltPFPuppi',
      applyWeight = True,
    )

    process.hltAK4PFPuppiJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK4PFPuppiJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK4PFPuppiJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK4PFPuppiHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK4PFPuppiJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK4PFPuppiJetCorrectorL1',
        'hltAK4PFPuppiJetCorrectorL2',
        'hltAK4PFPuppiJetCorrectorL3',
      ),
    )

    process.hltAK4PFPuppiJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK4PFPuppiJets'),
      correctors = cms.VInputTag('hltAK4PFPuppiJetCorrector'),
    )

    process.HLTAK4PFPuppiJetsSequence = cms.Sequence(
        process.hltAK4PFPuppiJets
      + process.hltAK4PFPuppiJetCorrectorL1
      + process.hltAK4PFPuppiJetCorrectorL2
      + process.hltAK4PFPuppiJetCorrectorL3
      + process.hltAK4PFPuppiJetCorrector
      + process.hltAK4PFPuppiJetsCorrected
    )

    ## AK8
    process.hltAK8PFPuppiJets = process.hltAK8PFJets.clone(
      src = 'hltParticleFlow',
      srcWeights = 'hltPFPuppi',
      applyWeight = True,
    )

    process.hltAK8PFPuppiJetCorrectorL1 = cms.EDProducer('L1FastjetCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L1FastJet'),
      srcRho = cms.InputTag('hltFixedGridRhoFastjetAll'),
    )

    process.hltAK8PFPuppiJetCorrectorL2 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L2Relative')
    )

    process.hltAK8PFPuppiJetCorrectorL3 = cms.EDProducer('LXXXCorrectorProducer',
      algorithm = cms.string('AK8PFPuppiHLT'),
      level = cms.string('L3Absolute')
    )

    process.hltAK8PFPuppiJetCorrector = cms.EDProducer('ChainedJetCorrectorProducer',
      correctors = cms.VInputTag(
        'hltAK8PFPuppiJetCorrectorL1',
        'hltAK8PFPuppiJetCorrectorL2',
        'hltAK8PFPuppiJetCorrectorL3',
      ),
    )

    process.hltAK8PFPuppiJetsCorrected = cms.EDProducer('CorrectedPFJetProducer',
      src = cms.InputTag('hltAK8PFPuppiJets'),
      correctors = cms.VInputTag('hltAK8PFPuppiJetCorrector'),
    )

    process.HLTAK8PFPuppiJetsSequence = cms.Sequence(
        process.hltAK8PFPuppiJets
      + process.hltAK8PFPuppiJetCorrectorL1
      + process.hltAK8PFPuppiJetCorrectorL2
      + process.hltAK8PFPuppiJetCorrectorL3
      + process.hltAK8PFPuppiJetCorrector
      + process.hltAK8PFPuppiJetsCorrected
    )

    ## MET
    process.hltPFPuppiMET = cms.EDProducer('PFMETProducer',
      alias = cms.string(''),
      applyWeight = cms.bool(True),
      calculateSignificance = cms.bool(False),
      globalThreshold = cms.double(0.0),
      parameters = cms.PSet(),
      src = cms.InputTag('hltParticleFlow'),
      srcWeights = cms.InputTag('hltPFPuppiNoLep'),
    )

    ## MET Type-1
    process.hltPFPuppiMETCorrection = cms.EDProducer('PFJetMETcorrInputProducer',
      jetCorrEtaMax = cms.double(9.9),
      jetCorrLabel = cms.InputTag('hltAK4PFPuppiJetCorrector'),
      jetCorrLabelRes = cms.InputTag('hltAK4PFPuppiJetCorrector'),
      offsetCorrLabel = cms.InputTag('hltAK4PFPuppiJetCorrectorL1'),
      skipEM = cms.bool(True),
      skipEMfractionThreshold = cms.double(0.9),
      skipMuonSelection = cms.string('isGlobalMuon | isStandAloneMuon'),
      skipMuons = cms.bool(True),
      src = cms.InputTag('hltAK4PFPuppiJets'),
      type1JetPtThreshold = cms.double(30.0),
    )

    process.hltPFPuppiMETTypeOne = cms.EDProducer('CorrectedPFMETProducer',
      src = cms.InputTag('hltPFPuppiMET'),
      srcCorrections = cms.VInputTag('hltPFPuppiMETCorrection:type1'),
    )

    process.HLTPFPuppiMETSequence = cms.Sequence(
        process.hltPFPuppiNoLep
      + process.hltPFPuppiMET
      + process.hltPFPuppiMETCorrection
      + process.hltPFPuppiMETTypeOne
    )

    ## Paths

    # Reconstruction path
    process.MC_JMEPFPuppi_v1 = cms.Path(
        process.HLTBeginSequence
      + process.hltPreMCJMEPFPuppi
      + process.HLTPFPuppiSequence
      + process.HLTAK4PFPuppiJetsSequence
      + process.HLTAK8PFPuppiJetsSequence
      + process.HLTPFPuppiMETSequence
      + process.HLTEndSequence
    )

    #### HLT paths development area
    # example customization for creating HLT_PFPuppiJet40_v1 path
    ## HLT_PFPuppiJet40_v1
    process.hltPrePFPuppiJet40 = cms.EDFilter("HLTPrescaler",
        L1GtReadoutRecordTag = cms.InputTag("hltGtStage2Digis"),
        offset = cms.uint32(0)
    )

    process.hltPFPuppiJetsCorrectedMatchedToCaloJets10 = cms.EDProducer("HLTPFJetsMatchedToFilteredCaloJetsProducer",
        maxDeltaR = cms.double(0.5),
        src = cms.InputTag("hltAK4PFPuppiJetsCorrected"),
        triggerJetsFilter = cms.InputTag("hltSingleCaloJet10"),
        triggerJetsType = cms.int32(85)
    )

    process.hltSinglePFPuppiJet40 = cms.EDFilter("HLT1PFJet",
        MaxEta = cms.double(5.0),
        MaxMass = cms.double(-1.0),
        MinE = cms.double(-1.0),
        MinEta = cms.double(-1.0),
        MinMass = cms.double(-1.0),
        MinN = cms.int32(1),
        MinPt = cms.double(40.0),
        inputTag = cms.InputTag("hltPFPuppiJetsCorrectedMatchedToCaloJets10"),
        saveTags = cms.bool(True),
        triggerType = cms.int32(85)
    )


    process.HLT_PFPuppiJet40_v1 = cms.Path(
        process.SimL1Emulator
      + process.HLTBeginSequence 
      + process.hltL1sZeroBias                # L1 seed
      + process.hltPrePFPuppiJet40            # prescale filter
      + process.HLTAK4CaloJetsSequence        # produce calo jets
      + process.hltSingleCaloJet10            # filter calos > 10 GeV (for matching - see later)  
      + process.HLTPFPuppiSequence            # produce pf particles and puppi weights
      + process.HLTAK4PFPuppiJetsSequence     # make AK4 jets reconstruction using puppi weights + calibrations
      + process.hltPFPuppiJetsCorrectedMatchedToCaloJets10  # match puppi to calo jets with dR<0.5 
      + process.hltSinglePFPuppiJet40              # filter puppi jets with pT>40GeV
      + process.HLTEndSequence
    )

    ## adding paths in "trigger menu"
    # modify this list of names with any new path
    newPathNames = [
       'HLT_PFPuppiJet40_v1'
    ] 
    
    # Adds the paths in the menu
    # for pathName in newPathNames:
    #    process.datasets.JetMET += cms.vstring(pathName)
    #    process.datasets.OnlineMonitor += cms.vstring(pathName)
    #    process.hltDatasetJetMET.triggerConditions += cms.vstring(pathName)
    #    process.hltDatasetOnlineMonitor.triggerConditions += cms.vstring(pathName + ' / 3')
    #    listOfPaths.append(pathName)
       
    # append new paths to schedule
    process.schedule.insert(0,process.MC_JMEPFPuppi_v1)
    #process.schedule.append(process.MC_JMEPFPuppi_v1)
    #print(process.schedule)
    # if process.schedule:
    #    print('adding PUPPI paths to schedule')
    #    #print(process.schedule)
    #    #process.schedule.revert()
    #    #print(process.schedule)
       
    #    #process.schedule_() = process.schedule_() +[process.MC_JMEPFPuppi_v1]
    #    #process.schedule_().revert()
    #    process.schedule.append(process.MC_JMEPFPuppi_v1)
    # #   process.schedule_().append(process.HLT_PFPuppiJet40_v1)

    return [process,listOfPaths]
