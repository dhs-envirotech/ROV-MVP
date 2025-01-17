import React from "react";
import {
  FaArrowUp,
  FaArrowDown,
  FaArrowLeft,
  FaArrowRight,
} from "react-icons/fa";

import PropTypes from "prop-types";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

const LogItem = () => {
  return (
    <p className="text-white font-mono text-sm mb-3">
      <p className="text-green-500 inline">12:01:02 1/14 </p>
      Hello world! I really love this! Very Cool!
    </p>
  );
};

const ArrowKeyButton = ({ buttonClass }) => {
  return (
    <div className="w-full h-full p-1 2xl:p-2">
      <button className="w-full h-full rounded-lg bg-gray-400 p-1 2xl:p-2">
        {React.createElement(buttonClass, {
          className: "w-full h-full text-slate-700",
        })}
      </button>
    </div>
  );
};

ArrowKeyButton.propTypes = {
  buttonClass: PropTypes.elementType.isRequired,
};

const App = () => {
  return (
    <div className="flex flex-col w-full h-full">
      <div className="h-20 bg-gray-400">e</div>
      <PanelGroup direction="horizontal">
        <Panel
          className="w-96 bg-black m-2 mr-1 p-6 rounded-xl flex flex-col"
          minSize={20}
          maxSize={30}
        >
          <h1 className="text-center text-white font-mono font-bold text-xl mb-2">
            Live Update Log
          </h1>
          <div className="flex-grow bg-gray-950 rounded-xl py-2 px-2">
            <LogItem />
            <LogItem />
            <LogItem />
          </div>
        </Panel>
        <PanelResizeHandle />
        <Panel className="flex-grow m-2 ml-1 bg-gray-200 p-4 rounded-xl flex flex-col">
          <div className="flex-grow flex-shrink overflow-auto">
            <div className="rounded-xl aspect-[4/3] m-auto max-h-full max-w-full align-middle bg-red-500"></div>
          </div>
          <div className="w-full mt-4 flex justify-center items-center h-32 2xl:h-52">
            <div className="w-48 h-28 2xl:w-72 2xl:h-48 rounded-xl bg-gray-300 grid grid-cols-3 grid-rows-2">
              <br />
              <ArrowKeyButton buttonClass={FaArrowUp} />
              <br />
              <ArrowKeyButton buttonClass={FaArrowLeft} />
              <ArrowKeyButton buttonClass={FaArrowDown} />
              <ArrowKeyButton buttonClass={FaArrowRight} />
            </div>
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
};

export default App;
