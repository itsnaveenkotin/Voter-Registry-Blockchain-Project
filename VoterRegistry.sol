// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VoterRegistry {
    struct Voter {
        bytes32 hashedId;
        string boothLocation;
        bool eligible;
    }

    Voter[] public voters;
    address public owner;
    mapping(bytes32 => bool) public voterExists;
    
    event VoterAdded(bytes32 indexed hashedId, string boothLocation);
    event RegistryReset();

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function addVoter(bytes32 _hashedId, string memory _boothLocation) external onlyOwner {
        require(!voterExists[_hashedId], "Voter already exists");
        voters.push(Voter(_hashedId, _boothLocation, true));
        voterExists[_hashedId] = true;
        emit VoterAdded(_hashedId, _boothLocation);
    }

    function checkVoter(bytes32 _hashedId) external view returns (bool eligible, string memory boothLocation) {
        require(voterExists[_hashedId], "Voter does not exist");
        for (uint i = 0; i < voters.length; i++) {
            if (voters[i].hashedId == _hashedId) {
                return (voters[i].eligible, voters[i].boothLocation);
            }
        }
        return (false, "");
    }

    function getAllVoters() external view returns (Voter[] memory) {
        return voters;
    }

    function resetRegistry() external onlyOwner {
        delete voters;
        emit RegistryReset();
    }

    function getVoterCount() external view returns (uint) {
        return voters.length;
    }
}