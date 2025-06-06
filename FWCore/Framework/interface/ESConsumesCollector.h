// -*- C++ -*-
#ifndef FWCore_Framework_ESConsumesCollector_h
#define FWCore_Framework_ESConsumesCollector_h
//
// Package:     FWCore/Framework
// Class  :     edm::ConsumesCollector
//
/**\class edm::ESConsumesCollector

 Description: Helper class to gather consumes information for the EventSetup.

 Usage: The constructor of an ESProducer module can get an instance of
        edm::ESConsumesCollector by calling consumesCollector()
        method. This instance can then be passed to helper classes in
        order to register the event-setup data the helper will request
        from an Event, LuminosityBlock or Run on behalf of the module.

 Caveat: The ESConsumesCollector should be used during the time that
         modules are being constructed. It should not be saved and
         used later. It will not work if it is used to call the
         consumes function during beginJob, beginRun, beginLuminosity
         block, event processing or at any later time. As of now, an
         ESConsumesCollector is provided for only ESProducer
         subclasses--i.e. those that call setWhatProduced(this, ...).
*/
//
// Original Author:  Kyle Knoepfel
//         Created:  Fri, 02 Oct 2018 12:44:47 GMT
//

#include "FWCore/Framework/interface/EventSetupRecordKey.h"
#include "FWCore/Framework/interface/DataKey.h"
#include "FWCore/Framework/interface/es_impl/MayConsumeChooser.h"
#include "FWCore/Utilities/interface/ESGetToken.h"
#include "FWCore/Utilities/interface/ESInputTag.h"
#include "FWCore/Utilities/interface/propagate_const.h"
#include "FWCore/Utilities/interface/Transition.h"

#include <vector>
#include <memory>

class testEventsetupRecord;

namespace edm {
  class ESConsumesCollectorAdaptor;
  class ESConsumesCollectorWithTagAdaptor;

  struct ESConsumesInfoEntry {
    ESConsumesInfoEntry(edm::eventsetup::EventSetupRecordKey const& iRecord,
                        edm::eventsetup::DataKey const& iProduct,
                        std::string moduleLabel,
                        std::unique_ptr<edm::eventsetup::impl::MayConsumeChooserCore> chooser)
        : recordKey_{iRecord},
          productKey_{iProduct},
          moduleLabel_{std::move(moduleLabel)},
          chooser_{std::move(chooser)} {}
    edm::eventsetup::EventSetupRecordKey recordKey_;
    edm::eventsetup::DataKey productKey_;
    std::string moduleLabel_;
    std::unique_ptr<edm::eventsetup::impl::MayConsumeChooserCore> chooser_;
  };
  using ESConsumesInfo = std::vector<ESConsumesInfoEntry>;

  class ESConsumesCollector {
  public:
    ESConsumesCollector() = delete;
    ESConsumesCollector(ESConsumesCollector const&) = delete;
    ESConsumesCollector(ESConsumesCollector&&) = default;
    ESConsumesCollector& operator=(ESConsumesCollector const&) = delete;
    ESConsumesCollector& operator=(ESConsumesCollector&&) = default;

    // ---------- member functions ---------------------------
    template <typename Product, typename Record>
    auto consumesFrom(ESInputTag const& tag) {
      using namespace edm::eventsetup;
      ESTokenIndex index{static_cast<ESTokenIndex::Value_t>(m_consumer->size())};
      m_consumer->emplace_back(EventSetupRecordKey::makeKey<Record>(),
                               DataKey(DataKey::makeTypeTag<Product>(), tag.data().c_str()),
                               tag.module(),
                               nullptr);
      //even though m_consumer may expand, the address for
      // name().value() remains the same since it is 'moved'.
      return ESGetToken<Product, Record>{m_produceMethodID, index, m_consumer->back().productKey_.name().value()};
    }

    template <typename Product, typename Record>
    auto consumesFrom() {
      using namespace edm::eventsetup;
      ESTokenIndex index{static_cast<ESTokenIndex::Value_t>(m_consumer->size())};
      m_consumer->emplace_back(
          EventSetupRecordKey::makeKey<Record>(), DataKey(DataKey::makeTypeTag<Product>(), ""), "", nullptr);
      //even though m_consumer may expand, the address for
      // name().value() remains the same since it is 'moved'.
      return ESGetToken<Product, Record>{m_produceMethodID, index, m_consumer->back().productKey_.name().value()};
    }

    ESConsumesCollectorAdaptor consumes();
    ESConsumesCollectorWithTagAdaptor consumes(ESInputTag tag);

  protected:
    explicit ESConsumesCollector(ESConsumesInfo* const iConsumer, unsigned int iProduceMethodID)
        : m_consumer{iConsumer}, m_produceMethodID{iProduceMethodID} {}

    template <typename Product, typename Record, typename Collector, typename PTag>
    auto registerMayConsume(std::unique_ptr<Collector> iCollector, PTag const& productTag) {
      //NOTE: for now, just treat like standard consumes request for the product needed to
      // do the decision
      iCollector->token() = consumes(productTag.inputTag());

      using namespace edm::eventsetup;
      ESTokenIndex index{static_cast<ESTokenIndex::Value_t>(m_consumer->size())};
      m_consumer->emplace_back(EventSetupRecordKey::makeKey<Record>(),
                               DataKey(DataKey::makeTypeTag<Product>(), "@mayConsume"),
                               "@mayConsume",
                               std::move(iCollector));
      //even though m_consumer may expand, the address for
      // name().value() remains the same since it is 'moved'.
      return ESGetToken<Product, Record>{m_produceMethodID, index, m_consumer->back().productKey_.name().value()};
    }

  private:
    // ---------- member data --------------------------------
    edm::propagate_const<ESConsumesInfo*> m_consumer{nullptr};
    unsigned int m_produceMethodID{0};
  };

  template <typename RECORD>
  class ESConsumesCollectorT : public ESConsumesCollector {
  public:
    ESConsumesCollectorT() = delete;
    ESConsumesCollectorT(ESConsumesCollectorT<RECORD> const&) = default;
    ESConsumesCollectorT(ESConsumesCollectorT<RECORD>&&) = default;
    ESConsumesCollectorT<RECORD>& operator=(ESConsumesCollectorT<RECORD> const&) = default;
    ESConsumesCollectorT<RECORD>& operator=(ESConsumesCollectorT<RECORD>&&) = default;

    // ---------- member functions ---------------------------

    using ESConsumesCollector::consumes;
    template <typename Product>
    auto consumes(ESInputTag const& tag) {
      return consumesFrom<Product, RECORD>(tag);
    }

    template <typename Product>
    auto consumes() {
      return consumesFrom<Product, RECORD>();
    }

    template <typename Product, typename FromRecord, typename Func, typename PTag>
    auto mayConsumeFrom(Func&& func, PTag const& productTag) {
      return registerMayConsume<Product, FromRecord>(
          std::make_unique<eventsetup::impl::MayConsumeChooser<RECORD, Product, FromRecord, Func, PTag>>(
              std::forward<Func>(func)),
          productTag);
    }

    template <typename Product, typename FromRecord, typename Func, typename PTag>
    ESConsumesCollector& setMayConsume(ESGetToken<Product, FromRecord>& token, Func&& func, PTag const& productTag) {
      token = mayConsumeFrom<Product, FromRecord>(std::forward<Func>(func), productTag);
      return *this;
    }

  private:
    //only ESProducer is allowed to make an instance of this class
    friend class ESProducer;
    friend class ESProducerExternalWork;
    friend class ::testEventsetupRecord;

    explicit ESConsumesCollectorT(ESConsumesInfo* const iConsumer, unsigned int iTransitionID)
        : ESConsumesCollector(iConsumer, iTransitionID) {}
  };

  class ESConsumesCollectorAdaptor {
  public:
    template <typename TYPE, typename REC>
    ESGetToken<TYPE, REC> consumes() {
      return m_consumer->template consumesFrom<TYPE, REC>();
    }

  private:
    //only ESConsumesCollector is allowed to make an instance of this class
    friend class ESConsumesCollector;
    explicit ESConsumesCollectorAdaptor(ESConsumesCollector* iBase) : m_consumer(iBase) {}

    ESConsumesCollector* m_consumer;
  };

  class ESConsumesCollectorWithTagAdaptor {
  public:
    template <typename TYPE, typename REC>
    ESGetToken<TYPE, REC> consumes() {
      return m_consumer->template consumesFrom<TYPE, REC>(m_tag);
    }

  private:
    //only ESConsumesCollector is allowed to make an instance of this class
    friend class ESConsumesCollector;
    ESConsumesCollectorWithTagAdaptor(ESConsumesCollector* iBase, ESInputTag iTag)
        : m_consumer(iBase), m_tag(std::move(iTag)) {}

    ESConsumesCollector* m_consumer;
    ESInputTag const m_tag;
  };

  inline ESConsumesCollectorAdaptor ESConsumesCollector::consumes() { return ESConsumesCollectorAdaptor(this); }
  inline ESConsumesCollectorWithTagAdaptor ESConsumesCollector::consumes(ESInputTag tag) {
    return ESConsumesCollectorWithTagAdaptor(this, std::move(tag));
  }

}  // namespace edm

#endif
