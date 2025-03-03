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
      vtxNdofCut = 4,
      vtxZCut=24,
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

    # change the JECs for corrected Jets tags
    process.hltAK4PFFastJetCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    process.hltAK4PFRelativeCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    process.hltAK4PFAbsoluteCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    process.hltAK4PFResidualCorrector.algorithm = cms.string('AK4PFPuppiHLT')
    

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

# This function converts all PF jets to PF+CHS jets.
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

