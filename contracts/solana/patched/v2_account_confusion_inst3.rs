// V2: Account confusion - Instance 3 (PATCHED)
// Fix: reward_vault typed as TokenAccount with address = state.reward_vault.

use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};

declare_id!("STAKING11111111111111111111111111111111111111");

#[program]
pub mod staking {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, reward_vault: Pubkey) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.reward_vault = reward_vault;
        state.bump = *ctx.bumps.get("state").unwrap();
        Ok(())
    }

    pub fn claim_rewards(ctx: Context<ClaimRewards>, amount: u64) -> Result<()> {
        ctx.accounts.state.total_claimed = ctx.accounts.state.total_claimed.wrapping_add(amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + State::SIZE,
        seeds = [b"state"],
        bump
    )]
    pub state: Account<'info, State>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ClaimRewards<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump)]
    pub state: Account<'info, State>,
    pub user: Signer<'info>,
    // FIX: typed as TokenAccount, address-constrained to state.reward_vault.
    #[account(address = state.reward_vault)]
    pub reward_vault: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct State {
    pub reward_vault: Pubkey,
    pub total_claimed: u64,
    pub bump: u8,
}

impl State {
    pub const SIZE: usize = 32 + 8 + 1;
}
